import os
import re
from datetime import datetime
from config import OUTPUT_DIR


class PRDService:
    def __init__(self):
        self.output_dir = OUTPUT_DIR

    def save_prd(self, content: str, product_name: str = None) -> str:
        """Save PRD content to a markdown file and return the filename."""
        # Extract product name from content if not provided
        if not product_name:
            product_name = self._extract_product_name(content)

        # Create a safe filename
        filename = self._create_filename(product_name)
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w") as f:
            f.write(content)

        return filename

    def _extract_product_name(self, content: str) -> str:
        """Extract product name from PRD content."""
        # Try to find the title in the first line
        lines = content.strip().split("\n")
        for line in lines:
            if line.startswith("# "):
                # Extract name before " - Product Requirements Document"
                title = line[2:].strip()
                if " - " in title:
                    return title.split(" - ")[0]
                return title
        return "Untitled"

    def _create_filename(self, product_name: str) -> str:
        """Create a safe filename from product name."""
        # Remove special characters and replace spaces with hyphens
        safe_name = re.sub(r"[^\w\s-]", "", product_name.lower())
        safe_name = re.sub(r"[\s_]+", "-", safe_name).strip("-")

        # Add timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        return f"{safe_name}-prd-{timestamp}.md"

    def _get_product_prefix(self, filename: str) -> str:
        """Extract the product name prefix from a filename."""
        # Remove .md extension
        name = filename.replace(".md", "")
        # Remove timestamp pattern like -20240113-143022
        name = re.sub(r"-\d{8}-\d{6}$", "", name)
        # Remove type suffixes
        name = re.sub(r"-prd$", "", name)
        name = re.sub(r"-competitive-analysis$", "", name)
        return name

    def _is_prd_file(self, filename: str) -> bool:
        """Check if a file is a PRD (not research)."""
        return "-prd-" in filename

    def _is_research_file(self, filename: str) -> bool:
        """Check if a file is a competitive analysis research file."""
        return "-competitive-analysis-" in filename

    def list_prds(self) -> list[dict]:
        """List all saved PRDs with their associated research files grouped."""
        prds = []
        research_files = []

        if os.path.exists(self.output_dir):
            for filename in os.listdir(self.output_dir):
                if filename.endswith(".md"):
                    filepath = os.path.join(self.output_dir, filename)
                    stat = os.stat(filepath)
                    created = datetime.fromtimestamp(stat.st_mtime)
                    file_info = {
                        "filename": filename,
                        "name": self._extract_name_from_filename(filename),
                        "date": created.strftime("%b %d, %Y"),
                        "created": created.isoformat(),
                        "size": stat.st_size,
                        "product_prefix": self._get_product_prefix(filename)
                    }

                    if self._is_prd_file(filename):
                        file_info["research"] = []
                        prds.append(file_info)
                    elif self._is_research_file(filename):
                        research_files.append(file_info)

        # Associate research files with their parent PRDs
        for research in research_files:
            for prd in prds:
                if research["product_prefix"] == prd["product_prefix"]:
                    prd["research"].append(research)
                    break

        # Sort PRDs by created date (newest first)
        prds = sorted(prds, key=lambda x: x["created"], reverse=True)

        # Sort research within each PRD by created date (newest first)
        for prd in prds:
            prd["research"] = sorted(prd["research"], key=lambda x: x["created"], reverse=True)

        return prds

    def _extract_name_from_filename(self, filename: str) -> str:
        """Extract a display name from the filename."""
        # Remove .md extension and timestamp suffix
        name = filename.replace(".md", "")
        # Remove timestamp pattern like -20240113-143022
        name = re.sub(r"-\d{8}-\d{6}$", "", name)
        # Remove -prd suffix
        name = re.sub(r"-prd$", "", name)
        # Remove -competitive-analysis suffix
        name = re.sub(r"-competitive-analysis$", "", name)
        # Convert dashes to spaces and title case
        name = name.replace("-", " ").title()
        return name

    def get_prd(self, filename: str) -> str:
        """Get the content of a saved PRD."""
        filepath = os.path.join(self.output_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return f.read()
        return None

    def append_to_prd(self, filename: str, content: str) -> bool:
        """
        Append content (like competitive analysis) to an existing PRD.

        Args:
            filename: The PRD filename to append to
            content: The content to append

        Returns:
            True if successful, False otherwise
        """
        filepath = os.path.join(self.output_dir, filename)
        if not os.path.exists(filepath):
            return False

        try:
            with open(filepath, "a") as f:
                f.write("\n\n" + content)
            return True
        except Exception:
            return False

    def save_research(self, content: str, product_name: str) -> str:
        """
        Save competitive research as a separate markdown file.

        Args:
            content: The research/analysis content
            product_name: Name of the product (for filename)

        Returns:
            The filename of the saved research
        """
        # Create a safe filename
        safe_name = re.sub(r"[^\w\s-]", "", product_name.lower())
        safe_name = re.sub(r"[\s_]+", "-", safe_name).strip("-")

        # Add timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        filename = f"{safe_name}-competitive-analysis-{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)

        # Add header to content
        full_content = f"# {product_name} - Competitive Analysis\n\n"
        full_content += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        full_content += "---\n\n"
        full_content += content

        with open(filepath, "w") as f:
            f.write(full_content)

        return filename

    def archive_prd(self, filename: str) -> bool:
        """
        Archive a PRD by moving it to the 'old' subdirectory.

        Args:
            filename: The PRD filename to archive

        Returns:
            True if successful, False otherwise
        """
        filepath = os.path.join(self.output_dir, filename)
        if not os.path.exists(filepath):
            return False

        # Create old directory if it doesn't exist
        old_dir = os.path.join(self.output_dir, "old")
        os.makedirs(old_dir, exist_ok=True)

        # Move file to old directory
        new_filepath = os.path.join(old_dir, filename)
        try:
            os.rename(filepath, new_filepath)
            return True
        except Exception:
            return False

    def archive_prd_with_research(self, filename: str) -> dict:
        """
        Archive a PRD and all its associated research files.

        Args:
            filename: The PRD filename to archive

        Returns:
            Dict with 'success' bool and 'archived' list of filenames
        """
        archived = []

        # Get the product prefix for this PRD
        product_prefix = self._get_product_prefix(filename)

        # Archive the PRD itself
        if self.archive_prd(filename):
            archived.append(filename)
        else:
            return {"success": False, "archived": []}

        # Find and archive all research files with matching prefix
        if os.path.exists(self.output_dir):
            for f in os.listdir(self.output_dir):
                if self._is_research_file(f) and self._get_product_prefix(f) == product_prefix:
                    if self.archive_prd(f):
                        archived.append(f)

        return {"success": True, "archived": archived}

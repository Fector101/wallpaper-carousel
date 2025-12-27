from pathlib import Path


class SpecFile:
    def __init__(self, path: str):
        self.path = Path(path)
        self.data = {}
        self._parse()

    def _parse(self):
        current_section = None

        for raw_line in self.path.read_text().splitlines():
            line = raw_line.strip()

            # skip empty lines and full-line comments
            if not line or line.startswith("#"):
                continue

            # section header
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                self.data.setdefault(current_section, {})
                continue

            # key = value lines
            if "=" in line and current_section:
                key, value = line.split("=", 1)

                key = key.strip()
                value = value.strip()

                # ignore commented keys like "# key = value"
                if key.startswith("#"):
                    continue

                self.data[current_section][key] = value

    def get(self, section: str, key: str, default=None):
        return self.data.get(section, {}).get(key, default)

    def section(self, section: str) -> dict:
        return self.data.get(section, {}).copy()

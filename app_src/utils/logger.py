import logging
import sys

class KivyColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\x1b[1;36m',    # bold cyan
        'INFO': '\x1b[1;92m',     # bold lime green
        'WARNING': '\x1b[1;93m',  # bold yellow
        'ERROR': '\x1b[1;91m',    # bold red
        'CRITICAL': '\x1b[1;95m', # bold magenta
    }
    RESET = '\x1b[0m'

    def format(self, record):
        level = record.levelname.ljust(7)
        name = record.name.ljust(14)
        msg = record.getMessage()

        if getattr(sys.stdout, "isatty", lambda: False)():
            color = self.COLORS.get(record.levelname, '')
            level = f"{color}{level}{self.RESET}"

        return f"[{level}] [{name}] {msg}"


app_logger = logging.getLogger("waller")

handler = logging.StreamHandler(sys.stdout)
formatter = KivyColorFormatter()
handler.setFormatter(formatter)

# Avoid duplicate logs if root logger is configured
app_logger.propagate = False
app_logger.addHandler(handler)
app_logger._configured = True




if __name__ == "__main__":
    from kivymd.app import MDApp
    app_logger.debug("Debug message - should not appear with INFO level")
    app_logger.info("Info message")
    app_logger.warning("Warning message")
    app_logger.error("Error message")
    app_logger.critical("Critical message")

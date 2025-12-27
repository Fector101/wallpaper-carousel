import logging


logger = logging.getLogger("android_widgets")
logger.addHandler(logging.NullHandler())
# logger.propagate = False #The point of package is to help developing with python on PC, so logs very Useful


# ANSI color codes
COLORS = {
    "DEBUG": "\033[36m",    # Cyan
    "INFO": "\033[32m",     # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",    # Red
    "CRITICAL": "\033[41m", # Red background
}
RESET = "\033[0m"


class BracketColorFormatter(logging.Formatter):
    def format(self, record):
        # Fixed-width levelname
        levelname = f"{record.levelname:<7}"
        color = COLORS.get(record.levelname, "")
        level_colored = f"{color}{levelname}{RESET}"

        # Fixed-width logger name
        name_fixed = f"{record.name:<15}"

        # Build the final string manually to avoid any extra spaces
        return f"[{level_colored}][{name_fixed}] {record.getMessage()}"


def enable_logging(level=logging.DEBUG):
    """Enable colored logging for android_widgets logger."""
    # Avoid adding multiple StreamHandlers
    if any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(BracketColorFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)

def disable_logging():
    """Disable colored logging for android_widgets logger."""
    # Remove all StreamHandlers (the ones we added in enable_colored_logging)
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            logger.removeHandler(handler)
    # Ensure logger stays silent
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.NOTSET)

# ------------------ Test ------------------
if __name__ == "__main__":
    enable_logging()
    logger.info("Found Layout: app_src/android/res/layout/image_test_widget.xml")

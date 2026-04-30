"""smart-report package."""

from .builder import Document, DocumentBuilder, document
from .containers.canvas import Canvas
from .containers.frame import Frame
from .containers.table import Table
from .elements.image import Image
from .elements.shape import Line, Rect
from .elements.spacer import Spacer
from .elements.text import Text

__version__ = "0.3.0"

__all__ = [
    "Canvas",
    "Document",
    "DocumentBuilder",
    "Frame",
    "Image",
    "Line",
    "Rect",
    "Spacer",
    "Table",
    "Text",
    "document",
]

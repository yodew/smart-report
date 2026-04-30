"""Core layout data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..style.color import RGBA
from ..style.units import AUTO, SizeSpec


class PositionMode(str, Enum):
    FLOW = "flow"
    ABSOLUTE = "absolute"


class OverflowMode(str, Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class Edges:
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0

    @property
    def horizontal(self) -> float:
        return self.left + self.right

    @property
    def vertical(self) -> float:
        return self.top + self.bottom

    @classmethod
    def all(cls, value: float) -> "Edges":
        return cls(top=value, right=value, bottom=value, left=value)


@dataclass(slots=True)
class Style:
    width: SizeSpec = AUTO
    height: SizeSpec = AUTO
    left: SizeSpec | None = None
    top: SizeSpec | None = None
    padding: Edges = field(default_factory=Edges)
    margin: Edges = field(default_factory=Edges)
    background: RGBA | None = None
    color: RGBA | None = None
    opacity: float = 1.0
    z_index: int = 0
    overflow: OverflowMode = OverflowMode.VISIBLE
    position: PositionMode = PositionMode.FLOW
    font_name: str = "Helvetica"
    font_size: float = 12.0
    line_height: float = 14.0
    border_radius: float = 0.0
    stroke_color: RGBA | None = None
    stroke_width: float = 0.0


@dataclass(slots=True)
class LayoutNode:
    node_type: str
    style: Style = field(default_factory=Style)
    content: dict[str, object] = field(default_factory=dict)
    children: list["LayoutNode"] = field(default_factory=list)
    name: str | None = None

    resolved_width: float = 0.0
    resolved_height: float = 0.0
    local_x: float = 0.0
    local_y: float = 0.0
    page_index: int = 0

    parent: "LayoutNode | None" = field(default=None, repr=False)

    def add_child(self, child: "LayoutNode") -> "LayoutNode":
        child.parent = self
        self.children.append(child)
        return child

    def remove_children_by_name(self, name: str) -> None:
        self.children = [child for child in self.children if child.name != name]
        for child in self.children:
            child.parent = self

    @property
    def flow_children(self) -> list["LayoutNode"]:
        return [child for child in self.children if child.style.position is PositionMode.FLOW]

    @property
    def absolute_children(self) -> list["LayoutNode"]:
        return [child for child in self.children if child.style.position is PositionMode.ABSOLUTE]

    @property
    def content_width(self) -> float:
        return max(0.0, self.resolved_width - self.style.padding.horizontal)

    @property
    def content_height(self) -> float:
        return max(0.0, self.resolved_height - self.style.padding.vertical)

    @property
    def creates_stacking_context(self) -> bool:
        return self.node_type in {"page", "canvas"}

    @property
    def is_renderable(self) -> bool:
        return self.node_type not in {"document", "page", "frame"}


@dataclass(frozen=True, slots=True)
class RenderItem:
    node: LayoutNode
    absolute_bounds: Rect
    clip_rects: tuple[Rect, ...]
    sort_key: tuple[int, ...]


def clone_layout_node(node: LayoutNode, include_children: bool = True) -> LayoutNode:
    cloned_style = Style(
        width=node.style.width,
        height=node.style.height,
        left=node.style.left,
        top=node.style.top,
        padding=Edges(
            top=node.style.padding.top,
            right=node.style.padding.right,
            bottom=node.style.padding.bottom,
            left=node.style.padding.left,
        ),
        margin=Edges(
            top=node.style.margin.top,
            right=node.style.margin.right,
            bottom=node.style.margin.bottom,
            left=node.style.margin.left,
        ),
        background=node.style.background,
        color=node.style.color,
        opacity=node.style.opacity,
        z_index=node.style.z_index,
        overflow=node.style.overflow,
        position=node.style.position,
        font_name=node.style.font_name,
        font_size=node.style.font_size,
        line_height=node.style.line_height,
        border_radius=node.style.border_radius,
        stroke_color=node.style.stroke_color,
        stroke_width=node.style.stroke_width,
    )
    cloned_node = LayoutNode(
        node_type=node.node_type,
        style=cloned_style,
        content=dict(node.content),
        name=node.name,
        resolved_width=node.resolved_width,
        resolved_height=node.resolved_height,
        local_x=node.local_x,
        local_y=node.local_y,
        page_index=node.page_index,
    )

    if include_children:
        for child in node.children:
            _ = cloned_node.add_child(clone_layout_node(child, include_children=True))

    return cloned_node

#!/usr/bin/env python3
"""Parse images containing Two Not Touch puzzle boards and print their
structures as CSV values.
"""

import argparse
from collections import namedtuple
import cv2 as cv
import numpy as np
from typing import Iterator, List, Optional, Union, Set, Tuple
import sys

WHITE = 255
ALMOST_WHITE = WHITE - 10
MID_GRAY = WHITE//2
DARK_GRAY = WHITE//4
BLACK = 0


class Point(namedtuple('Point', ['row', 'col'])):
    """A pixel coordinate point in an image."""
    def to_cv(self) -> Tuple[int, int]:
        """Return as an ``(x,y)`` tuple for use with OpenCV functions."""
        return (self.col, self.row)


class Rect(namedtuple('Rect', ['row', 'col', 'height', 'width'])):
    """A rectangular area in an image."""
    @classmethod
    def from_cv(cls, rect: Tuple[int, int, int, int]) -> 'Rect':
        """Convert from an OpenCV rect."""
        c_min, r_min, width, height = rect
        return Rect(r_min, c_min, height, width)

    def area(self) -> int:
        """The area of this rectangle in pixels."""
        return self.width * self.height

    def center(self) -> Point:
        """The point closest to the center of the rectangle."""
        return Point(self.row + self.height//2, self.col + self.width//2)

    def extract(self, img: np.ndarray) -> np.ndarray:
        """Extract the pixels bounded by this rectangle from the provided image."""
        return img[self.row:self.row + self.height, self.col:self.col + self.width]


def main() -> Optional[int]:
    args = parse_args()

    img = cv.imread(args.image, cv.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"error reading {args.image}")

    puzzles = find_puzzles(img)
    if not puzzles:
        raise RuntimeError(f"{args.image}: no puzzles found!")

    print(f"found {len(puzzles)} puzzle{'' if len(puzzles) == 1 else 's'}")
    print()

    for i, puzzle in enumerate(puzzles):
        print(f"Puzzle #{i+1}:")
        puzzle_img = puzzle.extract(img)

        regions, cells = parse_puzzle(puzzle_img)
        expected_cells = args.width * args.height
        if len(cells) != expected_cells:
            raise RuntimeError(f"{args.image}: found {len(cells)} cells, expected {expected_cells}!")

        locations = locate_cells(regions, cells, args.height)
        print()
        for row in locations:
            print(",".join(str(c) for c in row))
        print()


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    class Formatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
        pass

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=Formatter,
    )

    parser.add_argument(
        "image",
        help="an image containing Two Not Touch puzzle boards",
    )

    parser.add_argument(
        "--width",
        help="width of the puzzles in grid cells",
        default=10,
    )

    parser.add_argument(
        "--height",
        help="height of the puzzles in grid cells",
        default=10,
    )

    return parser.parse_args(args)


def find_puzzles(img: np.ndarray) -> List[Rect]:
    """Find one or more puzzle boards in an image."""
    return find_areas(img, find_black=True, fill_border=False)


def parse_puzzle(img: np.ndarray) -> Tuple[List[Set[Point]], List[Rect]]:
    """Find the regions and grid cells in a single puzzle image."""
    # find large regions by thresholding out the thin grid lines
    regions = find_regions(img)
    print(f"found {len(regions)} regions")

    cells = find_cells(img)
    print(f"found {len(cells)} grid cells")

    return regions, cells


def find_regions(img: np.ndarray) -> List[Set[Point]]:
    """Find large regions by thresholding out the thin grid lines."""
    return find_areas(img, all_points=True)


def find_cells(img: np.ndarray) -> List[Rect]:
    """Find individual grid cells by thresholding anything that's not almost white."""
    cells = find_areas(img, threshold=ALMOST_WHITE)

    # remove any cells whose area is 1/4 or less of the average size, on the
    # ground that they're probably glitches
    avg_area = sum(s.area() for s in cells) / len(cells)
    min_area = avg_area / 4
    cells = [s for s in cells if s.area() >= min_area]

    return cells


def find_areas(
        img: np.ndarray,
        threshold: int = MID_GRAY,
        fill_border: bool = True,
        find_black: bool = False,
        all_points: bool = False,
) -> List[Union[Rect, Set[Point]]]:
    """Find contiguous areas of the image with the same color (white by default).

    :param img: The image data
    :param threshold: The minimum color value to be considered white. Any color
        darker than this will be considered black.
    :param fill_border: Flood the image border with black before processing.
    :param find_black: Find black areas instead of white ones.
    :param all_points: Return areas as a set of all ``Point``s within that area.
        Default is false, which returns each area as a bounding ``Rect``.

    :returns: A list of areas found in the image, either as ``Rect``s or as sets
        of ``Point``s.
    """
    _, areas_img = cv.threshold(img, threshold, WHITE, cv.THRESH_BINARY)

    if fill_border:
        # add a 1px white border around the whole thing so we can flood fill
        # around the entire perimeter of the image, in case there are any
        # concavities in the puzzle border
        areas_img = cv.copyMakeBorder(areas_img, 1, 1, 1, 1, cv.BORDER_CONSTANT, value=WHITE)
        cv.floodFill(areas_img, None, (0,0), BLACK)

    rows, cols = areas_img.shape
    areas = []

    for row in range(rows):
        for col in range(cols):
            coord = Point(row, col)
            if areas_img[coord] == (BLACK if find_black else WHITE):
                # flood the area with dark gray
                _, _, _, rect = cv.floodFill(areas_img, None, coord.to_cv(), DARK_GRAY)

                # find all the pixels in this area
                if all_points:
                    area = {
                        Point(r,c) for r in range(rows) for c in range(cols)
                        if areas_img[r,c] == DARK_GRAY
                    }
                    areas.append(area)
                else:
                    areas.append(Rect.from_cv(rect))

                # replace with a different gray so we don't count these pixels
                # as part of the next area
                cv.floodFill(areas_img, None, coord.to_cv(), MID_GRAY)

    return areas


def locate_cells(regions: List[Set[Point]], cells: List[Rect], height: int) -> List[List[int]]:
    """Determine which region each cell is located in."""
    if height > 1:
        # sort cells by a lower-resolution version of their coords, to smooth over
        # minor variations due to thicker region lines
        min_row = min(s.row for s in cells)
        max_row = max(s.row for s in cells)
        row_separation = (max_row - min_row) // (height - 1)
        cells = sorted(cells, key=lambda s: (
            (s.row - min_row + row_separation//2) // row_separation, s.col
        ))

    locations = []
    for cell in cells:
        center = cell.center()
        for i, region in enumerate(regions):
            if center in region:
                locations.append(i)
                break
        else:
            raise RuntimeError(f"cell {cell} not found in any region")

    return list(partition_list(locations, height))


def partition_list(l: list, n: int) -> Iterator[list]:
    """Partition a list into sublists of length ``n``."""
    for i in range(0, len(l), n):
        yield l[i : i+n]


if __name__ == "__main__":
    sys.exit(main())

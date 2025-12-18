"""
Octo-Bresenham Interpolator
===========================

A novel algorithm for high-resolution terminal graphing using 8-dot Braille.
Treats each Braille character as a 2x4 pixel canvas and performs sub-character
line drawing to create connected, continuous vectors.

Key Innovation: Instead of plotting isolated points, this algorithm fills
intermediate dots to create solid lines within each character cell.

Author: Ryan Barrett
"""

import math
from typing import List, Tuple, Optional


class OctoBresenham:
    """
    Sub-character line drawing using 8-dot Braille as a 2x4 bitmap canvas.
    
    Coordinate System:
        Width:  2 columns (x ∈ {0, 1})
        Height: 4 rows (y ∈ {0, 1, 2, 3})
    
    Dot Layout:
        ┌───┬───┐
        │ 1 │ 4 │  y=0 (top)
        ├───┼───┤
        │ 2 │ 5 │  y=1
        ├───┼───┤
        │ 3 │ 6 │  y=2
        ├───┼───┤
        │ 7 │ 8 │  y=3 (bottom)
        └───┴───┘
        x=0   x=1
    """
    
    def __init__(self):
        # Base Unicode offset for Braille patterns
        self.base = 0x2800
        
        # Map (x, y) coordinates to dot bit values
        # x=0 is left column, x=1 is right column
        # y=0 is top row, y=3 is bottom row
        self.dot_map = {
            (0, 0): 0x01,  # Dot 1
            (1, 0): 0x08,  # Dot 4
            (0, 1): 0x02,  # Dot 2
            (1, 1): 0x10,  # Dot 5
            (0, 2): 0x04,  # Dot 3
            (1, 2): 0x20,  # Dot 6
            (0, 3): 0x40,  # Dot 7
            (1, 3): 0x80,  # Dot 8
        }
        
        # Precompute full column masks for efficiency
        self.left_col_full = 0x01 | 0x02 | 0x04 | 0x40   # ⡇
        self.right_col_full = 0x08 | 0x10 | 0x20 | 0x80  # ⢸

    def _get_dots_for_range(self, col: int, y_start: float, y_end: float) -> int:
        """
        Activates all dots in a column between y_start and y_end
        to create a solid vertical connector.
        
        Args:
            col: Column index (0=left, 1=right)
            y_start: Starting y coordinate (0.0-3.0)
            y_end: Ending y coordinate (0.0-3.0)
            
        Returns:
            Bitmask of activated dots
        """
        mask = 0
        
        # Determine range bounds
        low = min(int(round(y_start)), int(round(y_end)))
        high = max(int(round(y_start)), int(round(y_end)))
        
        # Clamp to valid range [0, 3]
        low = max(0, low)
        high = min(3, high)

        # Activate all dots in the range
        for y in range(low, high + 1):
            mask |= self.dot_map.get((col, y), 0)
            
        return mask

    def _get_single_dot(self, col: int, y: float) -> int:
        """Get the dot mask for a single point."""
        y_rounded = max(0, min(3, int(round(y))))
        return self.dot_map.get((col, y_rounded), 0)

    def render(self, data_stream: List[float], connect_chars: bool = True) -> str:
        """
        Render a data stream as continuous Braille waveform.
        
        Args:
            data_stream: List of floats normalized to range [0, 3]
            connect_chars: If True, attempts to connect adjacent characters
            
        Returns:
            String of Braille characters representing the waveform
        """
        if len(data_stream) < 2:
            return ""
            
        result = []
        prev_right_val = None
        
        # Process 2 data points at a time (left col, right col)
        for i in range(0, len(data_stream) - 1, 2):
            val_left = data_stream[i]
            val_right = data_stream[i + 1]
            
            char_mask = 0
            
            # --- Inter-character connection ---
            if connect_chars and prev_right_val is not None:
                # Bridge from previous character's right to this character's left
                if abs(prev_right_val - val_left) > 1.0:
                    mid = (prev_right_val + val_left) / 2
                    char_mask |= self._get_dots_for_range(0, val_left, mid)
            
            # --- Intra-character rendering ---
            
            # 1. Render base points for left and right columns
            char_mask |= self._get_single_dot(0, val_left)
            char_mask |= self._get_single_dot(1, val_right)
            
            # 2. The Bridge (Bresenham-lite interpolation)
            # If there's a significant gap, fill intermediate dots
            delta = abs(val_left - val_right)
            
            if delta > 1.0:
                # Calculate midpoint for bridging
                mid_val = (val_left + val_right) / 2
                
                # Fill left column towards midpoint
                char_mask |= self._get_dots_for_range(0, val_left, mid_val)
                
                # Fill right column from midpoint
                char_mask |= self._get_dots_for_range(1, mid_val, val_right)
                
            elif delta > 0.5:
                # Smaller gap: just extend each column slightly toward the other
                char_mask |= self._get_dots_for_range(0, val_left, val_left + (val_right - val_left) * 0.3)
                char_mask |= self._get_dots_for_range(1, val_right - (val_right - val_left) * 0.3, val_right)

            result.append(chr(self.base + char_mask))
            prev_right_val = val_right
            
        return "".join(result)

    def render_multi_row(self, data_stream: List[float], 
                         height: int = 4, 
                         width: Optional[int] = None) -> str:
        """
        Render data as a multi-row graph with specified height.
        
        Args:
            data_stream: Raw data values (will be normalized)
            height: Number of terminal rows to use
            width: Number of characters wide (None = auto from data)
            
        Returns:
            Multi-line string with the graph
        """
        if not data_stream:
            return ""
            
        # Normalize data to full range
        min_val = min(data_stream)
        max_val = max(data_stream)
        range_val = max_val - min_val if max_val != min_val else 1
        
        # Each row has 4 sub-rows (y=0 to y=3)
        total_sub_rows = height * 4
        
        # Normalize to [0, total_sub_rows - 1]
        normalized = [
            ((v - min_val) / range_val) * (total_sub_rows - 1)
            for v in data_stream
        ]
        
        # Build each row
        rows = []
        for row_idx in range(height):
            row_min = (height - 1 - row_idx) * 4
            row_max = row_min + 3
            
            # Map data to this row's coordinate space
            row_data = []
            for val in normalized:
                if val >= row_min and val <= row_max:
                    # Value is in this row
                    row_data.append(val - row_min)
                elif val > row_max:
                    # Value is above this row - show at top
                    row_data.append(0.0)
                else:
                    # Value is below this row - show at bottom
                    row_data.append(3.0)
            
            # Check if this row has any actual data
            has_data = any(
                row_min <= normalized[i] <= row_max 
                for i in range(len(normalized))
            )
            
            if has_data:
                rows.append(self.render(row_data))
            else:
                rows.append(" " * (len(row_data) // 2))
                
        return "\n".join(rows)


class OctoHeatmap:
    """
    Heatmap variant using dot density to represent intensity.
    
    Uses the number of active dots (0-8) to represent intensity levels,
    creating a visual "heat" effect.
    """
    
    def __init__(self):
        self.base = 0x2800
        
        # Precomputed patterns sorted by dot count (intensity)
        # Each level adds more dots in a visually pleasing pattern
        self.intensity_patterns = [
            0x00,                          # 0 dots: ⠀ (blank)
            0x40,                          # 1 dot:  ⡀ (bottom-left)
            0x40 | 0x80,                   # 2 dots: ⣀ (bottom row)
            0x40 | 0x80 | 0x04,            # 3 dots: ⣄
            0x40 | 0x80 | 0x04 | 0x20,     # 4 dots: ⣤
            0x40 | 0x80 | 0x04 | 0x20 | 0x02,  # 5 dots: ⣦
            0x40 | 0x80 | 0x04 | 0x20 | 0x02 | 0x10,  # 6 dots: ⣶
            0x40 | 0x80 | 0x04 | 0x20 | 0x02 | 0x10 | 0x01,  # 7 dots: ⣷
            0xFF,                          # 8 dots: ⣿ (full block)
        ]
    
    def render_heatmap(self, data_2d: List[List[float]], 
                       normalize: bool = True) -> str:
        """
        Render a 2D array as a heatmap using dot density.
        
        Args:
            data_2d: 2D array of values
            normalize: If True, normalize values to [0, 1]
            
        Returns:
            Multi-line string with heatmap
        """
        if not data_2d:
            return ""
            
        if normalize:
            # Find global min/max
            flat = [v for row in data_2d for v in row]
            min_val = min(flat)
            max_val = max(flat)
            range_val = max_val - min_val if max_val != min_val else 1
            
            data_2d = [
                [(v - min_val) / range_val for v in row]
                for row in data_2d
            ]
        
        rows = []
        for row in data_2d:
            chars = []
            for val in row:
                # Map [0, 1] to [0, 8] intensity levels
                level = int(round(val * 8))
                level = max(0, min(8, level))
                chars.append(chr(self.base + self.intensity_patterns[level]))
            rows.append("".join(chars))
            
        return "\n".join(rows)
    
    def render_gradient(self, width: int = 40) -> str:
        """Render a horizontal gradient to demonstrate intensity levels."""
        row = []
        for i in range(width):
            level = int((i / (width - 1)) * 8)
            row.append(chr(self.base + self.intensity_patterns[level]))
        return "".join(row)


class OctoSparkline:
    """
    Compact single-row sparkline using vertical position within characters.
    """
    
    def __init__(self):
        self.bresenham = OctoBresenham()
    
    def render(self, data: List[float], width: Optional[int] = None) -> str:
        """
        Render data as a compact sparkline.
        
        Args:
            data: Raw data values
            width: Desired character width (None = auto)
            
        Returns:
            Single-line sparkline string
        """
        if not data:
            return ""
            
        # Resample if width specified
        if width and len(data) != width * 2:
            resampled = []
            for i in range(width * 2):
                idx = int((i / (width * 2)) * len(data))
                resampled.append(data[min(idx, len(data) - 1)])
            data = resampled
        
        # Normalize to [0, 3]
        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val != min_val else 1
        
        normalized = [
            ((v - min_val) / range_val) * 3
            for v in data
        ]
        
        return self.bresenham.render(normalized)


def demo_sine_wave():
    """Demonstrate with a sine wave."""
    print("\n" + "=" * 60)
    print("  OCTO-BRESENHAM INTERPOLATOR - Sine Wave Demo")
    print("=" * 60)
    
    width = 60
    data = []
    for i in range(width * 2):
        angle = (i / 15.0) * math.pi
        val = (math.sin(angle) + 1) * 1.5
        data.append(val)
    
    renderer = OctoBresenham()
    output = renderer.render(data)
    
    print(f"\nInput Points: {len(data)}")
    print(f"Output Chars: {len(output)}")
    print(f"\n{output}")


def demo_complex_wave():
    """Demonstrate with a more complex waveform."""
    print("\n" + "=" * 60)
    print("  Complex Waveform (sine + harmonics)")
    print("=" * 60)
    
    width = 80
    data = []
    for i in range(width * 2):
        t = i / 20.0
        # Fundamental + harmonics
        val = math.sin(t * math.pi) * 0.6
        val += math.sin(t * math.pi * 2) * 0.25
        val += math.sin(t * math.pi * 3) * 0.15
        # Normalize to [0, 3]
        val = (val + 1) * 1.5
        data.append(val)
    
    renderer = OctoBresenham()
    output = renderer.render(data)
    print(f"\n{output}")


def demo_step_function():
    """Demonstrate interpolation on a step function."""
    print("\n" + "=" * 60)
    print("  Step Function (showing interpolation)")
    print("=" * 60)
    
    # Step function that jumps between levels
    data = []
    levels = [0, 3, 1, 2, 0, 3, 1.5, 2.5, 0, 3]
    for level in levels:
        data.extend([level] * 8)
    
    renderer = OctoBresenham()
    output = renderer.render(data)
    print(f"\n{output}")


def demo_heatmap():
    """Demonstrate the heatmap mode."""
    print("\n" + "=" * 60)
    print("  HEATMAP MODE - Dot Density Intensity")
    print("=" * 60)
    
    heatmap = OctoHeatmap()
    
    # Show intensity gradient
    print("\nIntensity Gradient (0% to 100%):")
    print(heatmap.render_gradient(40))
    
    # Create a simple 2D heatmap (Gaussian blob)
    print("\n2D Gaussian Heatmap:")
    size = 20
    data_2d = []
    for y in range(size):
        row = []
        for x in range(size):
            # Distance from center
            dx = (x - size/2) / (size/2)
            dy = (y - size/2) / (size/2)
            val = math.exp(-(dx*dx + dy*dy) * 2)
            row.append(val)
        data_2d.append(row)
    
    print(heatmap.render_heatmap(data_2d))


def demo_sparkline():
    """Demonstrate sparkline mode."""
    print("\n" + "=" * 60)
    print("  SPARKLINE MODE - Compact Data Visualization")
    print("=" * 60)
    
    sparkline = OctoSparkline()
    
    # Random walk
    import random
    random.seed(42)
    data = [50]
    for _ in range(199):
        data.append(data[-1] + random.gauss(0, 3))
    
    print("\nRandom Walk (200 points → 50 chars):")
    print(sparkline.render(data, width=50))
    
    # Stock-like pattern
    data = []
    for i in range(100):
        val = 50 + 20 * math.sin(i / 10) + 10 * math.sin(i / 3) + random.gauss(0, 2)
        data.append(val)
    
    print("\nStock-like Pattern:")
    print(sparkline.render(data, width=50))


def demo_comparison():
    """Compare standard vs Octo-Bresenham rendering."""
    print("\n" + "=" * 60)
    print("  COMPARISON: Standard Dots vs Octo-Bresenham")
    print("=" * 60)
    
    renderer = OctoBresenham()
    
    # Use sharp transitions to show the difference clearly
    print("\n1. Sharp Square Wave (where interpolation shines):")
    data = []
    for i in range(60):
        # Square wave with sharp transitions
        if (i // 6) % 2 == 0:
            data.append(0.0)
        else:
            data.append(3.0)
    
    # Standard: just individual dots
    print("\n   Standard (gaps at transitions):")
    standard_result = []
    for i in range(0, len(data) - 1, 2):
        mask = renderer._get_single_dot(0, data[i])
        mask |= renderer._get_single_dot(1, data[i + 1])
        standard_result.append(chr(0x2800 + mask))
    print("   " + "".join(standard_result))
    
    # Octo-Bresenham: connected
    print("\n   Octo-Bresenham (filled transitions):")
    print("   " + renderer.render(data))
    
    # Sawtooth wave
    print("\n2. Sawtooth Wave:")
    data = []
    for i in range(80):
        val = (i % 10) / 10.0 * 3.0
        data.append(val)
    
    print("\n   Standard:")
    standard_result = []
    for i in range(0, len(data) - 1, 2):
        mask = renderer._get_single_dot(0, data[i])
        mask |= renderer._get_single_dot(1, data[i + 1])
        standard_result.append(chr(0x2800 + mask))
    print("   " + "".join(standard_result))
    
    print("\n   Octo-Bresenham:")
    print("   " + renderer.render(data))
    
    # Steep sine wave
    print("\n3. Fast Sine Wave (high frequency):")
    data = []
    for i in range(80):
        angle = (i / 5.0) * math.pi
        val = (math.sin(angle) + 1) * 1.5
        data.append(val)
    
    print("\n   Standard:")
    standard_result = []
    for i in range(0, len(data) - 1, 2):
        mask = renderer._get_single_dot(0, data[i])
        mask |= renderer._get_single_dot(1, data[i + 1])
        standard_result.append(chr(0x2800 + mask))
    print("   " + "".join(standard_result))
    
    print("\n   Octo-Bresenham:")
    print("   " + renderer.render(data))


if __name__ == "__main__":
    demo_sine_wave()
    demo_complex_wave()
    demo_step_function()
    demo_heatmap()
    demo_sparkline()
    demo_comparison()
    
    print("\n" + "=" * 60)
    print("  All demos complete!")
    print("=" * 60)

#!/usr/bin/env python3
"""
QR Code Generator - Pure Python implementation
Generates valid QR codes with proper error correction, masking, and formatting.
Supports alphanumeric and byte mode encoding.
"""

import re

# QR Code constants
FORMAT_INFO_MASK = 0x5412  # Mask pattern for format info
MAX_VERSION = 1  # Starting with Version 1 (21x21)

# Galois field for Reed-Solomon error correction (GF(256) with primitive poly 0x11d)
GF_EXP = [0] * 512
GF_LOG = [0] * 256

def init_galois_field():
    """Initialize Galois field tables for Reed-Solomon."""
    x = 1
    for i in range(255):
        GF_EXP[i] = x
        GF_LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11d
    for i in range(255, 512):
        GF_EXP[i] = GF_EXP[i - 255]

def gf_mul(a, b):
    """Multiply two numbers in GF(256)."""
    if a == 0 or b == 0:
        return 0
    return GF_EXP[GF_LOG[a] + GF_LOG[b]]

def gf_pow(a, power):
    """Raise a to a power in GF(256)."""
    return GF_EXP[(GF_LOG[a] * power) % 255]

def gf_poly_mul(p, q):
    """Multiply two polynomials in GF(256)."""
    r = [0] * (len(p) + len(q) - 1)
    for j in range(len(q)):
        for i in range(len(p)):
            r[i + j] ^= gf_mul(p[i], q[j])
    return r

# Generator polynomials for Reed-Solomon error correction
RS_GENERATOR_POLYS = {}

def rs_generator_poly(nsym):
    """Generate Reed-Solomon generator polynomial for nsym correction bytes."""
    if nsym in RS_GENERATOR_POLYS:
        return RS_GENERATOR_POLYS[nsym]
    
    g = [1]
    for i in range(nsym):
        g = gf_poly_mul(g, [1, gf_pow(2, i)])
    
    RS_GENERATOR_POLYS[nsym] = g
    return g

def rs_encode_msg(msg, nsym):
    """Encode message with Reed-Solomon error correction."""
    gen = rs_generator_poly(nsym)
    remainder = list(msg) + [0] * nsym
    
    for i in range(len(msg)):
        coef = remainder[i]
        if coef != 0:
            for j in range(len(gen)):
                remainder[i + j] ^= gf_mul(gen[j], coef)
    
    return remainder  # Return full codeword (data + EC)

# QR Code capacity tables
# Version 1, L, M, Q, H correction levels
VERSION_CAPACITY = {
    1: {
        'L': {'data_codewords': 19, 'ec_codewords': 7, 'blocks': 1},
        'M': {'data_codewords': 16, 'ec_codewords': 10, 'blocks': 1},
        'Q': {'data_codewords': 13, 'ec_codewords': 13, 'blocks': 1},
        'H': {'data_codewords': 9, 'ec_codewords': 17, 'blocks': 1},
    }
}

# Mode indicators
MODE_NUMERIC = 1
MODE_ALPHANUMERIC = 2
MODE_BYTE = 4

# Alphanumeric character set
ALPHANUMERIC_CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:'
ALPHANUMERIC_MAP = {c: i for i, c in enumerate(ALPHANUMERIC_CHARS)}

# Format info strings for each error correction level and mask pattern
FORMAT_INFO_STR = {
    'L': [
        0x77c4, 0x72f3, 0x7daa, 0x789d, 0x662f, 0x6318, 0x6c41, 0x6976
    ],
    'M': [
        0x5412, 0x5125, 0x5e7c, 0x5b4b, 0x45f9, 0x40ce, 0x4f97, 0x4aa0
    ],
    'Q': [
        0x355f, 0x3068, 0x3f31, 0x3a06, 0x24b4, 0x2183, 0x2eda, 0x2bed
    ],
    'H': [
        0x1689, 0x13be, 0x1ce7, 0x19d0, 0x0762, 0x0255, 0x0d0c, 0x083b
    ]
}

def determine_mode(data):
    """Determine the best encoding mode for the data."""
    if all(c.isdigit() for c in data):
        return MODE_NUMERIC
    elif all(c in ALPHANUMERIC_CHARS for c in data):
        return MODE_ALPHANUMERIC
    else:
        return MODE_BYTE

def encode_data(data, mode):
    """Encode data into bitstream for QR code."""
    bits = []
    
    # Mode indicator (4 bits)
    bits.extend([(mode >> i) & 1 for i in range(3, -1, -1)])
    
    # Character count indicator (varies by mode and version)
    # Version 1: Numeric=10, Alphanumeric=9, Byte=8 bits
    if mode == MODE_NUMERIC:
        count_bits = 10
    elif mode == MODE_ALPHANUMERIC:
        count_bits = 9
    else:
        count_bits = 8
    
    count = len(data)
    bits.extend([(count >> i) & 1 for i in range(count_bits - 1, -1, -1)])
    
    # Data encoding
    if mode == MODE_NUMERIC:
        # Group digits in 3s, each group = 10 bits
        for i in range(0, len(data), 3):
            group = data[i:i+3]
            val = int(group)
            n_bits = 10 if len(group) == 3 else (4 if len(group) == 1 else 7)
            bits.extend([(val >> i) & 1 for i in range(n_bits - 1, -1, -1)])
    
    elif mode == MODE_ALPHANUMERIC:
        # Group characters in pairs, each pair = 11 bits
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                val = ALPHANUMERIC_MAP[data[i]] * 45 + ALPHANUMERIC_MAP[data[i+1]]
                n_bits = 11
            else:
                val = ALPHANUMERIC_MAP[data[i]]
                n_bits = 6
            bits.extend([(val >> i) & 1 for i in range(n_bits - 1, -1, -1)])
    
    elif mode == MODE_BYTE:
        # Each byte = 8 bits
        for byte in data.encode('utf-8'):
            bits.extend([(byte >> i) & 1 for i in range(7, -1, -1)])
    
    return bits

def pad_codewords(bits, capacity):
    """Pad bitstream to fill available codewords."""
    # Pad to multiple of 8
    while len(bits) % 8 != 0:
        bits.append(0)
    
    # Pad with alternating 236 and 17 bytes until capacity
    pad_bytes = [0b11101100, 0b00010001]
    pad_idx = 0
    while len(bits) < capacity * 8:
        byte_val = pad_bytes[pad_idx % 2]
        bits.extend([(byte_val >> i) & 1 for i in range(7, -1, -1)])
        pad_idx += 1
    
    return bits[:capacity * 8]

def bits_to_bytes(bits):
    """Convert bit list to byte list."""
    result = []
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits):
                byte = (byte << 1) | bits[i + j]
        result.append(byte)
    return result

class QRCode:
    """QR Code generator."""
    
    def __init__(self, data, ec_level='M'):
        init_galois_field()
        self.data = data
        self.ec_level = ec_level
        self.version = 1
        self.size = 21  # Version 1 = 21x21
        self.mask_pattern = 0
        self.modules = [[None] * self.size for _ in range(self.size)]
        self.generate()
    
    def generate(self):
        """Generate the QR code."""
        # Determine mode
        mode = determine_mode(self.data)
        
        # Get capacity for this version and EC level
        capacity_info = VERSION_CAPACITY[self.version][self.ec_level]
        data_capacity = capacity_info['data_codewords']
        ec_capacity = capacity_info['ec_codewords']
        
        # Encode data
        bits = encode_data(self.data, mode)
        bits = pad_codewords(bits, data_capacity)
        
        # Convert to bytes
        data_bytes = bits_to_bytes(bits)
        data_bytes = data_bytes[:data_capacity]
        
        # Add error correction
        codewords = rs_encode_msg(data_bytes, ec_capacity)
        
        # Create module placement
        self._add_finder_patterns()
        self._add_separators()
        self._add_alignment_patterns()
        self._add_timing_patterns()
        self._add_dark_module()
        self._reserve_format_areas()
        
        # Place data bits
        self._place_data_bits(codewords)
        
        # Apply mask and select best
        self._apply_best_mask()
        
        # Add format info
        self._add_format_info()
    
    def _is_reserved(self, row, col):
        """Check if a module position is reserved for special patterns."""
        size = self.size
        
        # Finder patterns (top-left, top-right, bottom-left)
        if (row < 9 and col < 9) or (row < 9 and col >= size - 8) or (row >= size - 8 and col < 9):
            return True
        
        # Timing patterns
        if row == 6 or col == 6:
            return True
        
        # Dark module
        if row == size - 8 and col == 8:
            return True
        
        # Version 1 has no version info, only format info
        # Format info areas
        if row == 8:
            if col < 9 or col >= size - 8:
                return True
        if col == 8:
            if row < 9 or row >= size - 7:
                return True
        
        return False
    
    def _add_finder_patterns(self):
        """Add finder patterns at corners."""
        pattern = [
            [1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [1, 0, 1, 1, 1, 0, 1],
            [1, 0, 1, 1, 1, 0, 1],
            [1, 0, 1, 1, 1, 0, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 1, 1]
        ]
        
        positions = [(0, 0), (0, self.size - 7), (self.size - 7, 0)]
        
        for r_start, c_start in positions:
            for r in range(7):
                for c in range(7):
                    self.modules[r_start + r][c_start + c] = pattern[r][c]
    
    def _add_separators(self):
        """Add separator white bands around finder patterns."""
        size = self.size
        
        # Top-left
        for i in range(8):
            if i < 7:
                self.modules[i][7] = 0
            if i < 7:
                self.modules[7][i] = 0
        self.modules[7][7] = 0
        
        # Top-right
        for i in range(8):
            if i < 7:
                self.modules[i][size - 8] = 0
            if i < 7:
                self.modules[7][size - 1 - i] = 0
        self.modules[7][size - 8] = 0
        
        # Bottom-left
        for i in range(8):
            if i < 7:
                self.modules[size - 8][i] = 0
            if i < 7:
                self.modules[size - 1 - i][7] = 0
        self.modules[size - 8][7] = 0
    
    def _add_alignment_patterns(self):
        """Add alignment patterns (none for version 1)."""
        pass  # Version 1 has no alignment patterns
    
    def _add_timing_patterns(self):
        """Add timing patterns."""
        size = self.size
        for i in range(8, size - 8):
            self.modules[6][i] = 0 if i % 2 else 1
            self.modules[i][6] = 0 if i % 2 else 1
    
    def _add_dark_module(self):
        """Add the dark module."""
        self.modules[self.size - 8][8] = 1
    
    def _reserve_format_areas(self):
        """Reserve areas for format info (mark as reserved by using None)."""
        size = self.size
        for i in range(9):
            if self.modules[i][8] is None:
                self.modules[i][8] = 'F'
            if self.modules[8][i] is None:
                self.modules[8][i] = 'F'
        for i in range(size - 8, size):
            if self.modules[i][8] is None:
                self.modules[i][8] = 'F'
        for i in range(size - 7, size):
            if self.modules[8][i] is None:
                self.modules[8][i] = 'F'
    
    def _place_data_bits(self, codewords):
        """Place data bits in the matrix."""
        bit_idx = 0
        total_bits = len(codewords) * 8
        
        # Start from bottom-right, go up in columns
        for col in range(self.size - 1, 0, -2):
            if col <= 6:  # Skip timing column
                col -= 1
            
            for row in range(self.size - 1, -1, -1):
                for c in [col, col - 1]:
                    if c < 0:
                        continue
                    
                    if self.modules[row][c] is None:
                        if bit_idx < total_bits:
                            byte_idx = bit_idx // 8
                            bit_in_byte = 7 - (bit_idx % 8)
                            bit = (codewords[byte_idx] >> bit_in_byte) & 1
                            self.modules[row][c] = bit
                        else:
                            self.modules[row][c] = 0  # Remainder bits
                        bit_idx += 1
            
            # Next column goes up (zigzag)
            col -= 2
            if col <= 6:
                col -= 1
            if col < 0:
                break
            
            for row in range(0, self.size):
                for c in [col + 1, col]:
                    if c < 0 or c >= self.size:
                        continue
                    
                    if self.modules[row][c] is None:
                        if bit_idx < total_bits:
                            byte_idx = bit_idx // 8
                            bit_in_byte = 7 - (bit_idx % 8)
                            bit = (codewords[byte_idx] >> bit_in_byte) & 1
                            self.modules[row][c] = bit
                        else:
                            self.modules[row][c] = 0
                        bit_idx += 1
    
    def _mask_func(self, row, col, pattern):
        """Apply mask function."""
        if pattern == 0:
            return (row + col) % 2 == 0
        elif pattern == 1:
            return row % 2 == 0
        elif pattern == 2:
            return col % 3 == 0
        elif pattern == 3:
            return (row + col) % 3 == 0
        elif pattern == 4:
            return (row // 2 + col // 3) % 2 == 0
        elif pattern == 5:
            return (row * col) % 2 + (row * col) % 3 == 0
        elif pattern == 6:
            return ((row * col) % 2 + (row * col) % 3) % 2 == 0
        elif pattern == 7:
            return ((row + col) % 2 + (row * col) % 3) % 2 == 0
        return False
    
    def _apply_best_mask(self):
        """Test all masks and apply the best one."""
        best_score = float('inf')
        best_pattern = 0
        
        # Save original modules
        original = [row[:] for row in self.modules]
        
        for pattern in range(8):
            # Reset modules
            for r in range(self.size):
                for c in range(self.size):
                    if original[r][c] in (0, 1):
                        self.modules[r][c] = original[r][c]
                    else:
                        self.modules[r][c] = None
            
            # Apply mask
            for r in range(self.size):
                for c in range(self.size):
                    if self.modules[r][c] is not None and self._is_data_module(r, c):
                        if self._mask_func(r, c, pattern):
                            self.modules[r][c] ^= 1
            
            # Simple score: count penalty patterns
            score = self._evaluate_mask()
            if score < best_score:
                best_score = score
                best_pattern = pattern
        
        self.mask_pattern = best_pattern
        
        # Apply best mask
        for r in range(self.size):
            for c in range(self.size):
                if original[r][c] in (0, 1):
                    self.modules[r][c] = original[r][c]
                else:
                    self.modules[r][c] = None
        
        for r in range(self.size):
            for c in range(self.size):
                if self.modules[r][c] is not None and self._is_data_module(r, c):
                    if self._mask_func(r, c, self.mask_pattern):
                        self.modules[r][c] ^= 1
    
    def _is_data_module(self, row, col):
        """Check if module is data (not finder pattern, timing, etc)."""
        size = self.size
        
        # Not finder patterns
        if (row < 9 and col < 9) or (row < 9 and col >= size - 8) or (row >= size - 8 and col < 9):
            return False
        
        # Not timing patterns
        if row == 6 or col == 6:
            return False
        
        return True
    
    def _evaluate_mask(self):
        """Evaluate mask quality (lower is better)."""
        score = 0
        size = self.size
        
        # Rule 1: Adjacent modules in row/column
        for r in range(size):
            count = 1
            for c in range(1, size):
                if self.modules[r][c] == self.modules[r][c-1] and self.modules[r][c] is not None:
                    count += 1
                else:
                    if count >= 5:
                        score += 3 + (count - 5)
                    count = 1
            if count >= 5:
                score += 3 + (count - 5)
        
        for c in range(size):
            count = 1
            for r in range(1, size):
                if self.modules[r][c] == self.modules[r-1][c] and self.modules[r][c] is not None:
                    count += 1
                else:
                    if count >= 5:
                        score += 3 + (count - 5)
                    count = 1
            if count >= 5:
                score += 3 + (count - 5)
        
        # Rule 2: Block of modules
        for r in range(size - 1):
            for c in range(size - 1):
                if (self.modules[r][c] == self.modules[r][c+1] == 
                    self.modules[r+1][c] == self.modules[r+1][c+1] and
                    self.modules[r][c] is not None):
                    score += 3
        
        # Rule 3: Finder pattern-like patterns
        finder_pattern = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0]
        finder_inv = [0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1]
        
        for r in range(size):
            for c in range(size - 10):
                row_slice = [self.modules[r][c+i] for i in range(11)]
                if row_slice == finder_pattern or row_slice == finder_inv:
                    score += 40
        
        for c in range(size):
            for r in range(size - 10):
                col_slice = [self.modules[r+i][c] for i in range(11)]
                if col_slice == finder_pattern or col_slice == finder_inv:
                    score += 40
        
        return score
    
    def _add_format_info(self):
        """Add format information."""
        format_info = FORMAT_INFO_STR[self.ec_level][self.mask_pattern]
        size = self.size
        
        # Add around top-left finder
        for i in range(6):
            self.modules[8][i] = (format_info >> i) & 1
        self.modules[8][7] = (format_info >> 6) & 1
        self.modules[8][8] = (format_info >> 7) & 1
        self.modules[7][8] = (format_info >> 8) & 1
        
        for i in range(9):
            self.modules[5-i][8] = (format_info >> i) & 1
        
        # Add near other finders
        self.modules[size-1][8] = (format_info >> 0) & 1
        self.modules[size-2][8] = (format_info >> 1) & 1
        self.modules[size-3][8] = (format_info >> 2) & 1
        self.modules[size-4][8] = (format_info >> 3) & 1
        self.modules[size-5][8] = (format_info >> 4) & 1
        self.modules[size-6][8] = (format_info >> 5) & 1
        self.modules[size-7][8] = (format_info >> 6) & 1
        self.modules[size-8][8] = (format_info >> 7) & 1
        
        for i in range(8):
            self.modules[8][size-8+i] = (format_info >> i) & 1
    
    def to_ascii(self, border=2):
        """Generate ASCII representation."""
        lines = []
        
        # Top border
        for _ in range(border):
            lines.append('██' * (self.size + 2 * border))
        
        for r in range(self.size):
            row = '██' * border
            for c in range(self.size):
                if self.modules[r][c] == 1:
                    row += '██'
                else:
                    row += '  '
            row += '██' * border
            lines.append(row)
        
        # Bottom border
        for _ in range(border):
            lines.append('██' * (self.size + 2 * border))
        
        return '\n'.join(lines)
    
    def to_unicode(self, border=2):
        """Generate Unicode block representation (smaller)."""
        lines = []
        
        # Top border
        for _ in range(border // 2):
            lines.append('█' * (self.size + 2 * border))
        
        for r in range(0, self.size, 2):
            row = '█' * border
            for c in range(self.size):
                top = self.modules[r][c] == 1 if r < self.size else False
                bottom = self.modules[r+1][c] == 1 if r+1 < self.size else False
                
                if top and bottom:
                    row += '█'
                elif top and not bottom:
                    row += '▀'
                elif not top and bottom:
                    row += '▄'
                else:
                    row += ' '
            row += '█' * border
            lines.append(row)
        
        # Bottom border
        for _ in range(border // 2):
            lines.append('█' * (self.size + 2 * border))
        
        return '\n'.join(lines)
    
    def to_svg(self, scale=10, border=4):
        """Generate SVG representation."""
        total_size = self.size + 2 * border
        pixel_size = total_size * scale
        
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {pixel_size} {pixel_size}" width="{pixel_size}" height="{pixel_size}">
  <rect width="{pixel_size}" height="{pixel_size}" fill="white"/>
'''
        
        for r in range(self.size):
            for c in range(self.size):
                if self.modules[r][c] == 1:
                    x = (c + border) * scale
                    y = (r + border) * scale
                    svg += f'  <rect x="{x}" y="{y}" width="{scale}" height="{scale}" fill="black"/>\n'
        
        svg += '</svg>'
        return svg


def main():
    import sys
    
    if len(sys.argv) > 1:
        data = sys.argv[1]
    else:
        data = "HELLO QR"
    
    ec_level = 'M'
    if len(sys.argv) > 2 and sys.argv[2].upper() in ['L', 'M', 'Q', 'H']:
        ec_level = sys.argv[2].upper()
    
    if len(data) > 25:
        print(f"Error: Data too long for Version 1 QR code (max ~25 alphanumeric chars)")
        print(f"Your data has {len(data)} characters")
        return
    
    # Generate QR code
    qr = QRCode(data, ec_level)
    
    # Print info
    mode = determine_mode(data)
    mode_name = {MODE_NUMERIC: 'Numeric', MODE_ALPHANUMERIC: 'Alphanumeric', MODE_BYTE: 'Byte'}[mode]
    
    print(f"QR Code Generator")
    print(f"=================")
    print(f"Data: '{data}'")
    print(f"Mode: {mode_name}")
    print(f"Error Correction: {ec_level}")
    print(f"Version: {qr.version}")
    print(f"Size: {qr.size}x{qr.size} modules")
    print(f"Mask Pattern: {qr.mask_pattern}")
    print()
    
    # Print QR code
    print(qr.to_unicode())
    print()
    
    # Save SVG file
    filename = f"qr_{re.sub(r'[^\w]', '_', data[:20])}.svg"
    with open(filename, 'w') as f:
        f.write(qr.to_svg())
    print(f"SVG saved to: {filename}")
    print()
    
    # Show data capacity info
    capacity = VERSION_CAPACITY[1][ec_level]
    print(f"Data capacity: {capacity['data_codewords']} codewords")
    print(f"EC capacity: {capacity['ec_codewords']} codewords")
    print(f"Can recover from up to ~{capacity['ec_codewords'] * 100 // (capacity['data_codewords'] + capacity['ec_codewords'])}% damage")


if __name__ == '__main__':
    main()

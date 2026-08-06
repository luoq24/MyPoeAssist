

def clamp(num, min_value, max_value):
    if num < min_value:
        return min_value
    elif num > max_value:
        return max_value
    else:
        return num


class BagBase(object):
    _SHRINK_BORDER = 2
    _SHRINK_DETECT = 3

    def __init__(self, x_min: int, x_max: int, x_size: int, y_min: int, y_max: int, y_size: int):        
        self._x_min = x_min
        self._x_max = x_max
        self._x_size = x_size
        self._y_min = y_min
        self._y_max = y_max
        self._y_size = y_size

        self._cell_w = (self._x_max - self._x_min) / self._x_size
        self._cell_h = (self._y_max - self._y_min) / self._y_size

    def _calc_coords_by_pos(self, x, y):
       coords_0 = int((x - self._x_min) / self._cell_w)
       coords_1 = int((y - self._y_min) / self._cell_h)

       coords_0 = clamp(coords_0, 0, self._x_size)
       coords_1 = clamp(coords_1, 0, self._y_size)

       return coords_0, coords_1
    
    def _calc_rect_by_shrink(self, x, y, shrink):
        c0, c1 = self._calc_coords_by_pos(x, y)

        x = int(self._x_min + c0 * self._cell_w) + shrink
        y = int(self._y_min + c1 * self._cell_h) + shrink
        w = int(self._cell_w) - 2 * shrink
        h = int(self._cell_h) - 2 * shrink

        return x, y, w, h
    
    def get_cell_center(self, col: int, row: int):
        x = int(self._x_min + (col + 0.5) * self._cell_w)
        y = int(self._y_min + (row + 0.5) * self._cell_h)
        return x, y

    def get_rect_border(self, x, y):
        return self._calc_rect_by_shrink(x, y, self._SHRINK_BORDER)

    def get_rect_detect(self, x, y):
        return self._calc_rect_by_shrink(x, y, self._SHRINK_DETECT)
    
    def _is_pos_in_rect(self, px, py, x, y, w, h):
        if x <= px <= x + w:
            if y <= py <= y + h:
                return True
            
        return False

    def is_pos_valid(self, px, py):
        x, y, w, h = self.get_rect_detect(px, py)

        return self._is_pos_in_rect(px, py, x, y, w, h)
    

class ChestPoe2(BagBase):
    def __init__(self):
        super().__init__(14, 647, 12, 160, 792, 12)

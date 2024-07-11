# utils.py
# Utility functions to support other code in this example project

import clr
import System
import System.Collections.Generic

timeout_seconds = 5.0
startup_timeout_seconds = 60.0

def WellRange(row: int, col: int, row_count: int, col_count: int) -> System.Collections.Generic.List[System.Tuple[System.Int32, System.Int32]]:
    retval = System.Collections.Generic.List[System.Tuple[System.Int32, System.Int32]](row_count * col_count)
    for r in range(row, row + row_count):
        for c in range(col, col + col_count):
            retval.Add(System.Tuple[System.Int32, System.Int32](r, c))
    return retval
    
row_map = { 
    'A':1,'a':1,
    'B':2,'b':2,
    'C':3,'c':3,
    'D':4,'d':4,
    'E':5,'e':5,
    'F':6,'f':6,
    'G':7,'g':7,
    'H':8,'h':8 }
    
def CellFromString(cell_string: str) -> (int, int):
    return (row_map[cell_string[0]], int(cell_string[1:]))
    
def WellRangeFromString(range_string: str) -> System.Collections.Generic.List[System.Tuple[System.Int32, System.Int32]]:
    cells = range_string.split(':')
    (start_row, start_col) = CellFromString(cells[0])
    
    # If only a single cell is specified
    if len(cells) == 1:
        return WellRange(start_row, start_col, 1, 1)
        
    (last_row, last_col) = CellFromString(cells[1])
    if last_row < start_row:
        t = start_row
        start_row = last_row
        last_row = t
    if last_col < start_col:
        t = start_col
        start_col = last_col
        last_col = t
        
    row_count = last_row - start_row + 1
    col_count = last_col - start_col + 1
    return WellRange(start_row, start_col, row_count, col_count)

def UniformValues(count: int, value: float) -> System.Collections.Generic.List[System.Double]:
    retval = System.Collections.Generic.List[System.Double](count)
    for i in range(count):
        retval.Add(value)
    return retval

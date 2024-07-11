# ls10.py
# A Python layer to wrap calls into the LS10 API (to keep other files uncluttered)

import clr
clr.AddReference("LSAPI")
import LS_API

import utils

def CreateNewDesign(design_name: str, project_name: str, comment: str) -> None:
    if design_name == '':
        raise Exception('design_name may not be empty')
    LS_API.LibraryStudioWrapper.CreateNewDesign(design_name, project_name, "", "", "", "", "", comment)

def AddLibrary(plate_name: str, rows: int, cols: int) -> None:
    LS_API.LibraryStudioWrapper.AddLibrary(plate_name, nRows=rows, nCols=cols)

def AddChemical(chemical_name: str, units: str) -> None:
    LS_API.LibraryStudioWrapper.AddChemical(chemical_name, 0x00000000, units)

def AddUniformMap(insert_position: int, source_chemical_name: str, destination_plate_name: str, units: str, volume: float, cell_range: str, tags: str) -> None:
    # insert_position is the 'step number' that will be given to the map, starting with 1. If you repeatedly add to position 1, then your recipe
    #  will be in reverse sequence of your calls to this function (each map being inserted before the one from the last call). It is recommended
    #  by this author to increment the insert_position with each call, starting with 1, so that the maps are sequenced in the same order as the
    #  calls to this function.
    wells = utils.WellRangeFromString(cell_range)
    values = utils.UniformValues(wells.Count, volume)
    LS_API.LibraryStudioWrapper.AddSourceMap(source_chemical_name, "Uniform", units, volume, wells, values, destination_plate_name, tags, insert_position, 1)
    
def WriteToDb() -> int:
    return LS_API.LibraryStudioWrapper.SaveDesignToDatabase(True, True)
    # todo: the library IDs are now known and can be written to the prompts and chemical manager files
    
def GetLibraries() -> list[LS_API.Library]:
    ls_libraries = LS_API.LibraryStudioWrapper.GetLibraries()
    return list[LS_API.Library](ls_libraries)

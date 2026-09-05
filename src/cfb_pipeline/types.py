import numpy as np
import numpy.typing as npt

type ImageArray = npt.NDArray[np.uint8]
# Region of a capture frame of the structure: [left, top, right, bottom]
type Region = tuple[int, int, int, int]

import numpy as np
from constants import realType

class mesh:

	def __init__(self, meshDict):
		self.xL 		= float(meshDict["xL"])
		self.xR 		= float(meshDict["xR"])
		self.numCells 	= int(meshDict["numCells"])
		self.numFaces 	= self.numCells + 1


class uniformMesh(mesh):

	def __init__(self, meshDict):
		super().__init__(meshDict)

		self.xFace 		= np.linspace(self.xL, self.xR, self.numCells + 1, dtype=realType)
		self.xCell 		= (self.xFace[1:] + self.xFace[:-1]) / 2.0
		self.dx 		= (self.xFace[1] - self.xFace[0]) * np.ones((self.numCells, 1), dtype=realType) # cell length
		self.dCellCent  = (self.xFace[1] - self.xFace[0]) * np.ones((self.numCells+1, 1), dtype=realType) # distance b/w cell centers, incl ghost cells

class nonuniformMesh(mesh):

	def __init__(self, meshDict):
		super().__init__(meshDict)
		raise RuntimeError("Nonuniform mesh not yet implemented")
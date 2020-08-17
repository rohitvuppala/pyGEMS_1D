import numpy as np
import matplotlib.pyplot as plt
from classDefs import parameters, geometry, gasProps
from solution import solutionPhys, boundaries, genInitialCondition
from spaceSchemes import calcRHS
from stateFuncs import calcStateFromPrim
# from romClasses import solutionROM
from inputFuncs import readRestartFile
import outputFuncs
import constants
import time
import os
import sys
import pdb

# driver function for advancing the solution
def solver(params: parameters, geom: geometry, gas: gasProps):

	# TODO: could move this to driver?
	# TODO: make an option to interpolate a solution onto the given mesh, if different
	# intialize from restart file
	if params.initFromRestart:
		params.solTime, solPrim0 = readRestartFile(params.restOutDir)
		solCons0, _, _, _ = calcStateFromPrim(solPrim0, gas)

	# otherwise init from scratch IC or custom IC file 
	else:
		if (params.initFile == None):
			solPrim0, solCons0 = genInitialCondition(params, gas, geom)
		else:
			# TODO: change this to .npz format with physical time included
			solPrim0 = np.load(params.initFile)
			solCons0, _, _, _ = calcStateFromPrim(solPrim0, gas)
	sol = solutionPhys(geom.numCells, solPrim0, solCons0, gas, params)
	
	# add bulk velocity if required
	# TODO: should definitely be moved somewhere else
	if (params.velAdd > 0.0):
		sol.solPrim[:,1] += params.velAdd
	
	sol.updateState(gas, fromCons = False)

	# initialize ROM
	if params.calcROM: 
		raise ValueError("ROM not implemented yet")
		# rom = solutionROM(params.romInputs, sol, params)
		# rom.initializeROMState(sol)
	else:
		rom = None

	# initialize boundary state
	bounds = boundaries(sol, params, gas)

	# prep probe
	# TODO: expand to multiple probe locations
	probeIdx = np.absolute(geom.x_cell - params.probeLoc).argmin()
	probeVals = np.zeros((params.numSteps, params.numVis), dtype = constants.floatType)

	# prep visualization
	if (params.visType != "None"): 
		fig, ax, axLabels = outputFuncs.setupPlotAxes(params)
		visName = ""
		for visVar in params.visVar:
			visName += "_"+visVar
		visName += "_"+params.simType

	tVals = np.linspace(params.dt, params.dt*params.numSteps, params.numSteps, dtype = constants.floatType)
	if ((params.visType == "field") and params.visSave):
		fieldImgDir = os.path.join(params.imgOutDir, "field_"+visName)
		if not os.path.isdir(fieldImgDir): os.mkdir(fieldImgDir)
	else:
		fieldImgDir = None


	# loop over time iterations
	for tStep in range(params.numSteps):
		
		print("Iteration "+str(tStep+1))
		# call time integration scheme
		advanceSolution(sol, rom, bounds, params, geom, gas)

		params.solTime += params.dt

		# write restart files
		if params.saveRestarts: 
			if ( ((tStep+1) % params.restartInterval) == 0):
				outputFuncs.writeRestartFile(sol, params, tStep)	 

		# write unsteady output
		if ( ((tStep+1) % params.outInterval) == 0):
			outputFuncs.storeFieldData(sol, params, tStep)
		outputFuncs.updateProbe(sol, params, probeVals, probeIdx, tStep)


		# draw visualization plots
		if ( ((tStep+1) % params.visInterval) == 0):
			if (params.visType == "field"): 
				outputFuncs.plotField(fig, ax, axLabels, sol, params, geom)
				if params.visSave: outputFuncs.writeFieldImg(fig, params, tStep, fieldImgDir)
			elif (params.visType == "probe"): 
				outputFuncs.plotProbe(fig, ax, axLabels, sol, params, probeVals, tStep, tVals)
			
	print("Solve finished, writing to disk")

	# write data to disk
	outputFuncs.writeData(sol, params, probeVals, tVals)

	# draw images, save to disk
	if ((params.visType == "probe") and params.visSave): 
		figFile = os.path.join(params.imgOutDir,"probe"+visName+".png")
		fig.savefig(figFile)

# numerically integrate ODE forward one physical time step
# TODO: add implicit time integrators
def advanceSolution(sol: solutionPhys, rom, bounds: boundaries, params: parameters, geom: geometry, gas: gasProps):

	solConsOuter = sol.solCons.copy()

	# loop over max subiterations
	for subiter in range(params.numSubIters):

		# compute RHS function
		calcRHS(sol, bounds, params, geom, gas)

		# advance solution/code
		# FOM
		if not params.calcROM:
			dSolCons = params.dt * params.subIterCoeffs[subiter] * sol.RHS

		# ROM
		else:
			raise ValueError("ROM not implemented yet")
			# rom.mapRHSToModels(sol)

			# # project onto test space
			# rom.calcProjection()
			# dSolCons = rom.advanceSubiter(sol, params, subiter)

		sol.solCons = solConsOuter + dSolCons
		sol.updateState(gas)
		

		# if implicit method, check residual and break if necessary

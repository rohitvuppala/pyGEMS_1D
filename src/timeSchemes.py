from solution import solutionPhys, boundaries
from romClasses import solutionROM
from classDefs import parameters, geometry, gasProps
from spaceSchemes import calcRHS
from boundaryFuncs import calcBoundaries
from Jacobians import calcDResDSolPrim, calcDResDSolPrimImag
import constants
import time
from scipy.sparse.linalg import spsolve
import numpy as np
import pdb

# compute fully-discrete residual
# TODO: cold start is not valid for timeOrder > 2
def calcImplicitRes(sol: solutionPhys, bounds: boundaries, params: parameters, geom: geometry, gas: gasProps, colstrt):
	
	t_or = params.timeOrder
	
	if (colstrt): # cold start
		params.timeOrder = 1 
	
	calcRHS(sol, bounds, params, geom, gas) # non-linear RHS of current solution
	
	if (params.timeOrder == 1):
		sol.res = (sol.solCons - sol.solHistCons[1])/(params.dt)
	elif (params.timeOrder == 2):
		sol.res = (1.5*sol.solCons - 2.*sol.solHistCons[1] + 0.5*sol.solHistCons[2])/(params.dt)
	elif (params.timeOrder == 3):
		sol.res = (11./6.*sol.solCons - 3.*sol.solHistCons[1] + 1.5*sol.solHistCons[2] -1./3.*sol.solHistCons[3])/(params.dt)
	elif (params.timeOrder == 4):
		sol.res = (25./12.*sol.solCons - 4.*sol.solHistCons[1] + 3.*sol.solHistCons[2] -4./3.*sol.solHistCons[3] + 0.25*sol.solHistCons[4])/(params.dt)
	else:
		raise ValueError("Implicit Schemes higher than BDF4 not-implemented")
	
	sol.res = -sol.res + sol.RHS
	params.timeOrder = t_or
	
	
# explicit time integrator, one subiteration
def advanceExplicit(sol: solutionPhys, rom: solutionROM, 
					bounds: boundaries, params: parameters, geom: geometry, gas: gasProps, 
					subiter, solOuter):
	
	
	#compute RHS function
	calcRHS(sol, bounds, params, geom, gas)
		
	# compute change in solution/code, advance solution/code
	if (params.calcROM):
		rom.mapRHSToModels(sol)
		rom.calcRHSProjection()
		rom.advanceSubiter(sol, params, subiter, solOuter)
	else:
		dSol = params.dt * params.subIterCoeffs[subiter] * sol.RHS
		sol.solCons = solOuter + dSol

	sol.updateState(gas)
	
	return sol
   
# implicit pseudo-time integrator, one subiteration
def advanceDual(sol, bounds, params, geom, gas, colstrt=False):
	
	# compute residual
	calcImplicitRes(sol, bounds, params, geom, gas, colstrt)

	# compute Jacobian or residual
	resJacob = calcDResDSolPrim(sol, gas, geom, params, bounds)
	
	# Comparing with numerical jacobians
	# diff = calcDResDSolPrimImag(sol, gas, geom, params, bounds, dt_inv, dtau_inv)
	# print(diff)

	# solve linear system 
	dSol = spsolve(resJacob, sol.res.flatten('C'))

	# update state
	sol.solPrim += dSol.reshape((geom.numCells, gas.numEqs), order='C')
	sol.updateState(gas, fromCons = False)

	# update history
	sol.solHistCons[0] = sol.solCons.copy() 
	sol.solHistPrim[0] = sol.solPrim.copy() 

	# compute linear solve residual	
	sol.res = resJacob @ dSol - sol.res.flatten('C')
	
	
	
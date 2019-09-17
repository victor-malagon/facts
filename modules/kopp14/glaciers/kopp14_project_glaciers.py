import numpy as np
import pickle
import sys
import os
import argparse
from scipy.stats import norm
from scipy.stats import t

''' kopp14_project_glaciers.py

This script runs the glacier projection task for the Kopp 2014 workflow. 
This task generates global contributions to sea-level change due to glacier and ice cap
melt.

Parameters: 
fitfile = Pickle file produced by kopp14_fit_glaciers.py
configfile = Pickle file produced by kopp14_preprocess_glaciers.py
nsamps = Numer of samples to produce
seed = Seed for the random number generator

Output: Pickle file containing...
gicsamps = Glacier and Ice Cap contributions to sea-level rise (nsamps, regions, years)

'''

def kopp14_project_glaciers(fitfile, configfile, nsamps, seed):
	
	# Load the fit file
	try:
		f = open(fitfile, 'rb')
	except:
		print("Cannot open fit file\n")
	
	# Extract the fit variables
	my_fit = pickle.load(f)
	f.close()
	
	meanGIC = my_fit["meanGIC"]
	T = my_fit["T"]	
	NGIC = my_fit["NGIC"]
	
	# Load the config file
	try:
		f = open(configfile, 'rb')
	except:
		print("Cannot open config file\n")
	
	# Extract the configuration variables
	my_config = pickle.load(f)
	f.close()
	
	targyears = my_config["targyears"]

	
	# Evenly sample an inverse normal distribution and permutate it
	# Note: This may be a bug being ported over from Kopp 2014 which could result in 
	# 		overconfident projections
	np.random.seed(seed)
	x = np.linspace(0,1,nsamps+2)[1:(nsamps+1)]
	norm_inv = norm.ppf(x)
	norm_inv_perm = np.full((T.shape[0], nsamps), np.nan)
	for i in np.arange(0,T.shape[0]):
		norm_inv_perm[i,:] = np.random.permutation(norm_inv)
	
	## Generate the samples --------------------------------------------------------------
	# Initialize variable to hold the samples
	gicsamps = np.full((nsamps, T.shape[0], len(targyears)), np.nan)
	
	# Loop over the target years
	for i in np.arange(0,len(targyears)):
		
		# Values to use for producing samples at this target year
		thisYear = targyears[i]
		thisMeanGIC = meanGIC[:,i]
		thisT = T[:,:,i]
		thisNGIC = NGIC[i]
		
		# Generate the samples for this year
		if(thisNGIC > 0):
			temp = t.ppf(norm.cdf(norm_inv_perm), np.min((np.inf,thisNGIC-1))).T
			gicsamps[:,:,i] = np.dot(temp, thisT) + thisMeanGIC
		else:
			gicsamps[:,:,i] = np.nan

	# Save the global thermal expansion projections to a pickle
	output = {"gicsamps": gicsamps}
	outfile = open(os.path.join(os.path.dirname(__file__), "kopp14_glaciers_projections.pkl"), 'wb')
	pickle.dump(output, outfile)
	outfile.close()


if __name__ == '__main__':
	
	# Initialize the command-line argument parser
	parser = argparse.ArgumentParser(description="Run the glacier projection stage for the Kopp14 SLR projection workflow",\
	epilog="Note: This is meant to be run as part of the Kopp14 module within the Framework for the Assessment of Changes To Sea-level (FACTS)")
	
	# Define the command line arguments to be expected
	parser.add_argument('--nsamps', '-n', help="Number of samples to generate [default=20000]", default=20000, type=int)
	parser.add_argument('--seed', '-s', help="Seed value for random number generator [default=1234]", default=1234, type=int)
	
	parser.add_argument('--fit_file', help="Fit file produced in the glaciers fitting stage",\
	default=os.path.join(os.path.dirname(__file__), "kopp14_glaciers_fit.pkl"))
	
	parser.add_argument('--config_file', help="Configuration file produced in the glaciers preprocessing stage",\
	default=os.path.join(os.path.dirname(__file__), "kopp14_glaciers_config.pkl"))
	
	# Parse the arguments
	args = parser.parse_args()
	
	# Run the projection process on the files specified from the command line argument
	kopp14_project_glaciers(args.fit_file, args.config_file, args.nsamps, args.seed)
	
	exit()
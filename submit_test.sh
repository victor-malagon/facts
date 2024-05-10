#!/bin/sh
#SBATCH --partition=HMEMS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --job-name=facts_test
#SBATCH --error=job.%J.err
#SBATCH --output=job.%J.out
#SBATCH --mail-user=victor.malagon.santos@nioz.nl
#SBATCH --mail-type=FAIL,END

module load R
. $HOME/facts_gia/ve3/bin/activate
#python3 runFACTS.py experiments/dummy > job.log 2>&1
python3 runFACTS.py test.ssp585 > job_ssp585.log 2>&1

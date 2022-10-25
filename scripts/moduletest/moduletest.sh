#!/bin/bash

# This script is intended to be used to support
# the development of scripts that call
# modules for testing purposes outside the FACTS EnTK framework.

echo "Initiating test in $WORKDIR..."

mkdir $WORKDIR
cd $WORKDIR

cp -L -r $TESTSCRIPT_DIR/../* .

echo ""
echo "Extracting data files..."
for i in data/*
do
    tar xzf $i  2>&1 | grep -v 'Ignoring'
done

echo ""
echo "Executing workflow..."

j=0
for i in "${STAGES[@]}"
do
    j=$(( $j+1 ))
    EXECCMD="python ${STAGE_SCRIPT[j]} ${STAGEOPTIONS[j]}"
    echo $EXECCMD
    $EXECCMD
done


echo ""
echo "Collecting output files..."
if ! [[ -d $OUTPUT_DIR ]]
then
    mkdir $OUTPUT_DIR
fi

ls ${PIPELINE_ID}*.nc
mv ${PIPELINE_ID}*.nc $OUTPUT_DIR

cd $TESTSCRIPT_DIR

if [[ ! -v PRESERVE_WORKDIR ]]; then
    rm -fr $WORKDIR
fi
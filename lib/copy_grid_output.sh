#!/bin/bash

run=$1
data_path=$2
output_path=$3
lappd_EB_path=$4
run_type=$5

IFDH="$(cd "$(dirname "$0")" && pwd)/ifdh.sh"

# Overwrite not enabled for ifdh cp - skip the file if it exists in /persistent
file_exists() {
    if [ -e "$1" ]; then
        return 0  # File exists
    else
        return 1  # File does not exist
    fi
}

# create destination folders and make them editable/writable
mkdir -p $data_path/R$run
chmod 777 $data_path/R$run
# only laser and beam runs will have LAPPDs
if [ "$run_type" == "beam" ] || [ "$run_type" == "laser" ] || [ "$run_type" == "beam_39" ]; then
    mkdir -p $lappd_EB_path/LAPPDTree/R$run
    chmod 777 $lappd_EB_path/LAPPDTree/R$run
    mkdir -p $lappd_EB_path/offsetFit/R$run
    chmod 777 $lappd_EB_path/offsetFit/R$run
fi

# copy processed files

echo ""
echo "Copying ProcessedData Files..."
echo ""

# ProcessedData files
for file in "$output_path/$run/Processed"*; do
    filename=$(basename "$file")
    if ! file_exists "$data_path/R$run/$filename"; then
        "${IFDH}" cp "$file" "$data_path/R$run/"
    else
        echo "File $filename already exists in $data_path/R$run/. Skipping..."
    fi
done


# LAPPD-related EB files (LAPPDTree + offsetFit result)
if [ "$run_type" == "beam" ] || [ "$run_type" == "laser" ] || [ "$run_type" == "beam_39" ]; then

    echo ""
    echo "Copying LAPPD Files..."
    echo ""

    for file in "$output_path/$run/LAPPDTree"*; do
        filename=$(basename "$file")
        if ! file_exists "$lappd_EB_path/LAPPDTree/R$run/$filename"; then
            "${IFDH}" cp "$file" "$lappd_EB_path/LAPPDTree/R$run/"
        else
            echo "File $filename already exists in $lappd_EB_path/LAPPDTree/R$run/. Skipping..."
        fi
    done

    for file in "$output_path/$run/offsetFitResult"*; do
        filename=$(basename "$file")
        if ! file_exists "$lappd_EB_path/offsetFit/R$run/$filename"; then
            "${IFDH}" cp "$file" "$lappd_EB_path/offsetFit/R$run/"
        else
            echo "File $filename already exists in $lappd_EB_path/offsetFit/R$run/. Skipping..."
        fi
    done
fi


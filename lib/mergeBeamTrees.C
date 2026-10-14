#include <TFile.h>
#include <TTree.h>
#include <TChain.h>
#include <iostream>
#include <TSystem.h>
#include <TSystemDirectory.h>
#include <TList.h>
#include <TSystemFile.h>

// Function to merge root files
void mergeBeamTrees(const std::string &directory, int runNumber, const std::string &file_name, const std::string &tree_name) {
    // Define the file directory based on the run number and output file name
    std::string runDirectory = directory + "/" + std::to_string(runNumber) + "/";
    std::string outputFileName = file_name + "_" + std::to_string(runNumber) + ".root";
    
    // Create a TChain to merge trees
    TChain chain(tree_name.c_str());

    // Create directory object
    TSystemDirectory dir(runDirectory.c_str(), runDirectory.c_str());
    TList *files = dir.GetListOfFiles();
    
    if (files) {
        TSystemFile *file;
        TString fname;
        TIter next(files);
        while ((file = (TSystemFile*)next())) {
            fname = file->GetName();
            // Normal BeamCluster root files
            if (file_name != "LAPPDBeamCluster" && fname.BeginsWith(file_name + "_") && fname.EndsWith(".root") && !fname.EndsWith(".lappd.root")) {
                std::string filePath = runDirectory + fname.Data();
                std::cout << "Adding file: " << filePath << std::endl;
                chain.Add(filePath.c_str());
            }
            // LAPPD BeamCluster root files
            else if (file_name == "LAPPDBeamCluster" && fname.EndsWith(".lappd.root")) {
                std::string filePath = runDirectory + fname.Data();
                std::cout << "Adding LAPPD file: " << filePath << std::endl;
                chain.Add(filePath.c_str());
            }
        }
    }

    // Create a new ROOT file and save the merged tree
    TFile outputFile(outputFileName.c_str(), "RECREATE");
    // Using fast clone, works only for files with identical tree structure
    // Merges within a minute
    TTree *mergedTree = chain.CloneTree(-1, "fast");
    mergedTree->Write();

    // Write and close the file
    outputFile.Close();
    
    std::cout << "Merged tree saved to " << outputFileName << std::endl;
}

// Wrapper function to merge root trees with provided directory path and run number
void mergeBeamTreesWrapper(const std::string &directory, int runNumber, const std::string &file_name, const std::string &tree_name) {
    mergeBeamTrees(directory, runNumber, file_name, tree_name);
}

// Entry point for the ROOT macro
void mergeBeamTrees(const char* dir, int runNumber, const char* file_name, const char* tree_name) {
    mergeBeamTreesWrapper(std::string(dir), runNumber, std::string(file_name), std::string(tree_name));
}

% Script for preparing a final version mat file after topas
% This script designed to be executed in the task_X folder
clc, clear
taskNumber = 18;
numOfSamples = 1;
ii = 1;
for i = 1:numOfSamples
    disp(['step 1_', num2str(i)])
    clearvars -except taskNumber i ii numOfSamples
    try
        load(['./output/ws_topas_', num2str(taskNumber, '%.2u'), '_', num2str(i, '%.6u'), '.mat']);
        tmp = load(['./auxiliary/aux_', num2str(taskNumber, '%.2u'), '_', num2str(i, '%.6u'), '.mat']);

        cst = tmp.cst;
        dij = tmp.dij;
        resultGUI.physicalDose = tmp.resultGUI.physicalDose;

        clear tmp
        save(['./final/final_', num2str(taskNumber, '%.2u'), '_', num2str(ii, '%.6u'), '.mat']);
        ii = ii + 1;
        
    catch
        warning('wasnt able to load')
    end    
    
end

addpath(genpath(pwd))
imsize = 9; 
depth = 80;

for j = 1:numOfSamples
    
    disp(['step 2_', num2str(j)])
    clearvars -except taskNumber j numOfSamples imsize depth
    
    load(['./final/final_', num2str(taskNumber, '%.2u'), '_', num2str(j, '%.6u'), '.mat']);
    V = [cst{:,4}];
    V = unique(vertcat(V{:}));
    eraseCtDensMask = ones(prod(ct.cubeDim),1);
    eraseCtDensMask(V) = 0;
    resultGUI.MC_physicalDose(eraseCtDensMask == 1) =  0;
    resultGUI.MC_physicalDose(resultGUI.MC_physicalDose < 1e-4) = 0;
    [inputcube, dosecube] = matRad_rayTracingXXX(ct.cube, ...
        {resultGUI.MC_physicalDose}, ct.resolution,stf.isoCenter,2, ...
        stf.gantryAngle,stf.couchAngle, imsize, depth);
    
    dosecube = dosecube/resultGUI.w;
    save(['./cubes_8099N/inpOutCubes_', num2str(j, '%.6u'), '.mat'], 'inputcube', 'dosecube');




end

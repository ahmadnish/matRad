% Script for preparing a final version mat file after topas
% This script designed to be executed in the task_X folder
clc, clear
taskNumber = 21;
numOfSamples = 1000;
ii = 1;
% for i = 1:numOfSamples
%     disp(['step 1_', num2str(i)])
%     clearvars -except taskNumber i ii numOfSamples
%     try
%         load(['\\ad\fs\E040-McMegaMuscleDisk\Nish\task_21\output\ws_topas_', num2str(taskNumber, '%.2u'), '_', num2str(i, '%.6u'), '.mat']);
%         tmp = load(['\\ad\fs\E040-McMegaMuscleDisk\Nish\task_21\auxiliary\aux_', num2str(taskNumber, '%.2u'), '_', num2str(i, '%.6u'), '.mat']);
% 
%         cst = tmp.cst;
%         dij = tmp.dij;
%         resultGUI.physicalDose = tmp.resultGUI.physicalDose;
% 
%         clear tmp
%         save(['./final/final_', num2str(taskNumber, '%.2u'), '_', num2str(ii, '%.6u'), '.mat']);
%         ii = ii + 1;
%         
%     catch
%         warning('wasnt able to load')
%     end    
%     
% end

addpath(genpath(pwd))
imsize = 15; 
depth = 120;
load('./vars_21.mat')
for j = 60
    tic
    disp(['step 2_', num2str(j)])
    clearvars -except taskNumber j numOfSamples imsize depth vars
    
    jj = find([vars.gantryAngle] == j);
    jj = jj(1);
    load(['./final/final_', num2str(taskNumber, '%.2u'), '_', num2str(jj, '%.6u'), '.mat']);
    V = [cst{:,4}];
    V = unique(vertcat(V{:}));
    eraseCtDensMask = ones(prod(ct.cubeDim),1);
    eraseCtDensMask(V) = 0;
    resultGUI.MC_physicalDose(eraseCtDensMask == 1) =  0;
    resultGUI.MC_physicalDose(resultGUI.MC_physicalDose < 1e-4) = 0;
    [inputcube, dosecube_MC, dosecube_phys] = matRad_rayTracingXXX(ct.cube, ...
        {resultGUI.MC_physicalDose}, {resultGUI.physicalDose}, ct.resolution,stf.isoCenter,2, ...
        stf.gantryAngle,stf.couchAngle, imsize, depth);
    
    t = max(max(dosecube_MC(:)), max(dosecube_phys(:)))
    clf
    hold on
    subplot(211)
    imagesc(squeeze(dosecube_MC(:,7,:)))
    title('Monte Carlo Dose')
    
    caxis('manual')
    caxis([0 t])
    colorbar;
    
    subplot(212)
    imagesc(squeeze(dosecube_phys(:,7,:)))
    title('Analytical Dose')
    
    caxis('manual')
    caxis([0 t])
    colorbar;
    
    pause(.1)
    
    %figure, plot(squeeze(dosecube(7,7,:)))
    %clf
    %dosecube = dosecube/resultGUI.w;
    toc
%     save(['./cubes_1501515N/inpOutCubes_', num2str(j, '%.6u'), '.mat'], 'inputcube', 'dosecube');




end

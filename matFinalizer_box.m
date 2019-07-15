% Script for preparing a final version mat file after topas for box phantom
clc, clear
mkdir('c:\matRad\nishTopas\task_13\cubes')

numOfSamples = 2500;
ii = 1;
for i = 1:numOfSamples
    tic
    
    disp(['step 1_', num2str(i)])
    clearvars -except taskNumber i ii numOfSamples
    
    load(['\\ad\fs\E040-McMegaMuscleDisk\Nish\output_13\ws_topas_05_', num2str(i, '%.6u'), '.mat']);

    resultGUI.MC_physicalDose(resultGUI.MC_physicalDose < 1e-4) = 0;
    
    dosecube = resultGUI.MC_physicalDose(40:119,73:87, 73:87);
    inputcube = ct.cube{1}(40:119,73:87, 73:87);

    dosecube = dosecube/resultGUI.w;

    t = dosecube .* inputcube;
    dosecube = 1000 * dosecube / sum(t(:));
   
    toc
    
    save(['c:/matRad/nishTopas/task_13/cubes/inpOutCubes_', num2str(i, '%.6u'), '.mat'], 'inputcube', 'dosecube');
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Script for preparing patient training set for ANN 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clc,clear
addpath(genpath(pwd))

taskNumber = 36;
foldername = ['C:\matRad\nishTopas\task_', num2str(taskNumber, '%.2u')];

% set up the folders
if exist(foldername, 'dir') ~= 7
    mkdir(foldername)
    mkdir([foldername, '\auxiliary'])
    mkdir([foldername, '\matfiles'])
    mkdir([foldername, '\output'])
    mkdir([foldername, '\final'])
    mkdir([foldername, '\cubes'])
    mkdir([foldername, '\figures'])
    addpath(genpath(foldername))
end


% prepare a description file of the task
fid = fopen([foldername, '\discription.txt'], 'wt' );
description = ['preparing a Pencil Beam for Paper figure'];
% discription = ['Using patient case S000005 from HIT data ', ...
%     '\n to test the network -- all around angles ', ...
%     '\n Preparing ouputs for the PAPER'];
% fprintf( fid, '%\n', discription);
fwrite(fid, description, 'char'); 
fclose(fid);

% Load machine data
load protons_generic_TOPAS_cropped.mat
particleEnergies = [machine.data.energy];

% set up the gantry and iso center shift change domain
gantryAngles = [40:5:90];
% couchAngles = 0:5:355;
isoCenterShift = [0 0];

numOfSamples = 1;
%%
tmp2 = 0;
i = 1;
vars = struct;
while (i <= numOfSamples)
    
    vars(i).gantryAngle = randsample(gantryAngles, 1);
%     vars(i).couchAngle = randsample(couchAngles, 1);
    vars(i).shift = randsample(isoCenterShift, 1);
    vars(i).energy = particleEnergies(16);
    
    
    % check if there is recurrence in sampling
    tmp1 = 1;
    for ii = 1:i-1
        if (isequal(vars(i), vars(ii)))
            tmp1 = 0;
        end
    end
    
    if tmp1
        i = i+1;
    else 
        tmp2 = tmp2+1;
    end
end

save(['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/vars_', num2str(taskNumber, '%.2u'), '.mat'], 'vars');
%%
addpath(genpath(pwd))
tic
Ws = zeros(numOfSamples, 1);
tmp = 0;
for i = 1:numOfSamples
    
    disp(i)
    clearvars -except vars Ws tmp i taskNumber
    
    [ct, cst] = load('C:/matRad/S000005_ID-20171221.mat');
    pln.radiationMode = 'protons';
    ct.numOfCtScen = 1;
    ct = matRad_calcWaterEqD(ct, pln);
    
    [ct, cst, pln, dij, stf, resultGUI] = doseCalc_patient(vars(i), ct, cst);
    clc, close

    if isnan(resultGUI.w)
        warning('no fluence were assigned')
        disp(i)
        tmp = tmp + 1;
        continue
    end
    
    
%     
    

%     filename = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/full_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u')];
%     save(filename);

    Vars = vars(i);
    
    filename = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/auxiliary/aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    save(filename, 'cst', 'dij', 'resultGUI', 'Vars');

    
%     nishSliceWrapper(ct, cst, pln, resultGUI.physicalDose, true, filename3)

    
    % prune the input for topas, save what is necessary
    tt = resultGUI;
    clear resultGUI
    resultGUI.w = tt.w;
    clear tt
    ct = rmfield(ct, 'cubeHU');
    disp(resultGUI.w)
    Ws(i) = resultGUI.w;
    
    filename = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/matfiles/topas_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    save(filename, 'ct', 'pln', 'resultGUI', 'stf');
    
end
toc
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Script for preparing training set for ANN 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clc,clear
addpath(genpath(pwd))
%% Write down all the possible values for the parameters
taskNumber = 13;
foldername = ['.\nishTopas\task_', num2str(taskNumber, '%.2u')];
override = true
while true
    if 7 == exist(foldername, 'dir')
        taskNumber = taskNumber + 1;
        foldername = ['.\nishTopas\task_', num2str(taskNumber, '%.2u')]
    else
        if override
            taskNumber = taskNumber - 1;
            foldername = ['.\nishTopas\task_', num2str(taskNumber, '%.2u')]
            status = rmdir(foldername, 's')
        end
        status = mkdir(foldername)
        foldername = ['.\nishTopas\task_', num2str(taskNumber, '%.2u'),'\auxiliary']
        status = mkdir(foldername)
        break
    end
end
    
load protons_generic_TOPAS_cropped.mat

finalCubeSize = [80 28 28]; % the extraction cube for ANN

particleEnergies = [machine.data.energy];
peakPos = [machine.data.peakPos];

% for now energy is 104 and hardcoded by loading the stf
% particleEnergies = particleEnergies(7:28); % 22 cases
% peakPos = peakPos(7:28); 

slabSPs = 0.05:.1:2.5; % 26 cases
tissueSps = .8:.1:1.2; % 5 cases
slabXs = 0:15; % 16 cases (adaptive)
slabYs = 8:21; % 14 cases
slabZs = 0:8; % 9 cases
alignmentsX = -40:0; % 41 cases
slabGeometeries = ["Rectangle", "Ellipsoid", "Pyramid", "2DPyramid"]; % 4 cases

% for the 1 case
% slabSPs = 2; % 26 cases
% tissueSps = 1; % 5 cases
% slabXs = 3; % 16 cases (adaptive)
% slabYs = 14; % 14 cases
% slabZs = 3; % 9 cases
% alignmentsX = -10; % 41 cases
% slabGeometeries = ["Rectangle","Rectangle"]; % 4 cases

numOfSamples = 5;
%% Random sample from the possible values
vars = struct;
i = 1;
tmp2 = 0;
while (i <= numOfSamples && tmp2 < 10)
    
    vars(i).boxSize = 160 * ones(1,3);
    vars(i).res = 2 * ones(1,3);
%     vars(i).gantryAngle = 0;
%     vars(i).couchAngle = 0;
    vars(i).geoShape = randsample(slabGeometeries, 1);
%     vars(i).Energy = randsample(particleEnergies, 1); % desired energy for the particle
    vars(i).Energy = particleEnergies(16);
%     peakPosition = peakPos(vars(i).Energy == particleEnergies);
%     peakPosition = peakPosition/vars(i).res(3);
    
    vars(i).alignment = [0 -15 0]; 
    vars(i).alignment(1) = randsample(alignmentsX,1);
    
    vars(i).geoSize = zeros(1,3);
    
    tmp = slabXs(vars(i).alignment(1) - slabXs > -41);
    if numel(tmp) == 1
        vars(i).geoSize(1) = tmp;
    else
        vars(i).geoSize(1) = randsample(tmp,1);
    end
    
    vars(i).geoSize(2) = randsample(slabYs,1); % slabYs; for the 1 case
    vars(i).geoSize(3) = randsample(slabZs,1); % slabZs; for the 1 case
    
    vars(i).slab_sp = randsample(slabSPs,1); % slab's stopping power ##  slabSPs; %for the 1 case 
    vars(i).tissue_sp = randsample(tissueSps, 1); % tissue's stopping power ## tissueSps; %for the 1 case 
    
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

save(['./nishTopas/task_', num2str(taskNumber, '%.2u'), '/vars_', num2str(taskNumber, '%.2u'), '.mat'], 'vars');

tic
for i = 1:numOfSamples
    disp(i)
    [ct, cst, pln, dij, stf, resultGUI, mask] = doseCalc(vars(i));
    close
    
    filename1 = ['./nishTopas/task_', num2str(taskNumber, '%.2u'), '/topas_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    filename2 = ['./nishTopas/task_', num2str(taskNumber, '%.2u'), '/auxiliary/aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    
    Vars = vars(i);
    save(filename2, 'ct', 'cst', 'pln', 'dij', 'resultGUI', 'stf', 'Vars');
    
    tmp = resultGUI;
    clear resultGUI
    resultGUI.w = tmp.w;
    clear tmp
    ct = rmfield(ct, 'cubeHU');
%     
    save(filename1, 'ct', 'pln', 'dij', 'cst', 'resultGUI', 'stf');
end
toc
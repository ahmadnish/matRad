%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Script for preparing training set for ANN 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clc,clear
addpath(genpath(pwd))
%% Write down all the possible values for the parameters
taskNumber = 8;
foldername = ['.\nishTopas\task_', num2str(taskNumber, '%.2u')];
override = false
while true
    if 7 == exist(foldername, 'dir')
        taskNumber = taskNumber + 1;
        foldername = ['.\nishTopas\task_', num2str(taskNumber, '%.2u')]
    else
        if 7 == exist(foldername, 'dir') && override
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

% particleEnergies = particleEnergies(7:28); % 22 cases
% peakPos = peakPos(7:28); 

slabSPs = 0.05:.1:2.5; % 26 cases
tissueSps = .8:.1:1.2; % 5 cases
slabXs = 0:15; % 16 cases (adaptive)
slabYs = 8:21; % 14 cases
slabZs = 0:8; % 9 cases
alignmentsX = -40:0; % 41 cases
slabGeometeries = ["Rectangle", "Ellipsoid", "Pyramid", "2DPyramid"]; % 4 cases

% slabGeometeries = ["Rectangle", "2DPyramid"];
numOfSamples = 10000;
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
    
    vars(i).geoSize(2) = randsample(slabYs,1);
    vars(i).geoSize(3) = randsample(slabZs(),1); 
    
    vars(i).slab_sp = randsample(slabSPs,1); % slab's stopping power
    vars(i).tissue_sp = randsample(tissueSps, 1); % tissue's stopping power
    
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

save(['./nishTopas/task_07/vars_', num2str(taskNumber, '%.2u'), '.mat'], 'vars');

tic
for i = 1:numOfSamples
    disp(i)
    [ct, cst, pln, dij, stf, resultGUI, mask] = doseCalc(vars(i));
    close
    
    filename1 = ['./nishTopas/task_07/topas_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    filename2 = ['./nishTopas/task_07/auxiliary/aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    
    Vars = vars(i);
    save(filename2, 'ct', 'cst', 'pln', 'dij', 'resultGUI', 'stf', 'Vars');
    
    tmp = resultGUI;
    clear resultGUI
    resultGUI.w = tmp.w;
    clear tmp
    ct = rmfield(ct, 'cubeHU');
    
    save(filename1, 'ct', 'pln', 'resultGUI', 'stf');
end
toc
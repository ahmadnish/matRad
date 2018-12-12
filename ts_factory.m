% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% % Script for preparing training set for ANN 
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clc, , clear, close all
%% Write down all the possible values for the parameters
load protons_generic_TOPAS_cropped.mat

particleEnergies = [machine.data.energy];
peakPos = [machine.data.peakPos];

particleEnergies = particleEnergies(7:28); %22 cases
peakPos = peakPos(7:28); 

slabSPs = [0.00324:.01:2.53061]; %253 cases
slab_goe_xs = 0;
slabGeometeries = ["Rectangle", "Circle", "Pyramid"];

%% Random sample from the possible values
vars.gantryAngle = 0;
vars.couchAngle = 0;
vars.geo.shape = 'Pyramid';
vars.geo.size = [8 15 8]; % size of the geometry in voxels
                % for Rectagle:
                % for Triangle:
                % for Circle:
                
vars.alignment = [-30 -16 0]; % aligns the center point in respect to the
                       % isocneter which in turn will be the starting point
                       % for building the geometry. y and z are build around
                       % this point while x is build toward left or right
                       % first dimension y: up to down
                       % second dimension x: left to right
                       % third dimension 

vars.slab_ed = 2; % slab's electron density
vars.slab_hu = 1024; % slab's Hounsfield's unit

vars.Energy = 127.5440; % desired energy for the particle

% load('BOXPHANTOM_2mm.mat')
[ct, cst] = makeBoxphantom(160,160,160);

[ct, cst, pln, stf, resultGUI] = doseCalc(ct, cst, vars);
close

% filename = ['topas_ws_',int2str(slab_loc(1)),'_',int2str(slab_loc(2)), ...
%     '_',int2str(slab_loc(3)),'_',int2str(geo(1)),'_',int2str(geo(2)), ...
%     '_',int2str(geo(3))];

filename = ['topas_ws'];

save([filename, '.mat']);

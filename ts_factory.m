% Load The Boxphantom
clc, clear, close all


vars.gantryAngle = 0;
vars.couchAngle = 0;
vars.geo.shape = 'Rec';
vars.geo.size = [3 15 3]; % size of the geometry in voxels
                % for Rectagle:
                % for Triangle:
                % for Circle:
                
vars.alignment = [-10 -1 0]; % aligns the center point in respect to the
                       % isocneter which in turn will be the starting point
                       % for building the geometry. y and z are build around
                       % this point while x is build toward left or right
                       % first dimension y: up to down
                       % second dimension x: left to right
                       % third dimension 

vars.slab_ed = 2; % slab's electron density
vars.slab_hu = 1024; % slab's Hounsfield's unit

vars.Energy = 116.3620; % desired energy for the particle

load('BOXPHANTOM_2mm.mat')

[ct, cst, pln, stf, resultGUI] = doseCalc(ct, cst, vars);

% filename = ['topas_ws_',int2str(slab_loc(1)),'_',int2str(slab_loc(2)), ...
%     '_',int2str(slab_loc(3)),'_',int2str(geo(1)),'_',int2str(geo(2)), ...
%     '_',int2str(geo(3))];

filename = ['topas_ws'];

save([filename, '.mat']);

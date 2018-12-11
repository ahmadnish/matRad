function [ct, cst, pln, stf, resultGUI] = slabgeometry(ct, cst, vars)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% takes the vars as the variables regarding the slab and does the dose
% calculations
%
%   call:
%         [ct, cst, pln, stf, resultGUI] = slabgeometry(ct, cst, vars)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

pln.radiationMode = 'protons';
pln.machine = 'generic_TOPAS_cropped';

%%
% setting up the plan
pln.numOfFractions        = 30;
pln.propStf.gantryAngles  = vars.gantryAngle;
pln.propStf.couchAngles   = vars.couchAngle;
pln.propStf.bixelWidth    = 150;
pln.propStf.longitudinalSpotSpacing = 150;
pln.propStf.numOfBeams    = numel(pln.propStf.gantryAngles);
pln.propStf.isoCenter     = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);
pln.propOpt.runDAO        = 0;
pln.propOpt.runSequencing = 0;

% slab geometry and alignment
geo = vars.geo;
alignment = vars.alignment;

% setting up dose with realistic numbers considering it's one bixel and
% only one fraction
cst{2,6}.dose = .2;
cst{2,6}.dose = .5;

pln.propOpt.bioOptimization = 'none';

% reading the isocenter
slab_loc = pln.propStf.isoCenter; 

% turning it into voxels and aligning it
slab_loc(1) = floor(slab_loc(1)/ct.resolution.y) + alignment(1);
slab_loc(2) = floor(slab_loc(2)/ct.resolution.x) + alignment(2);
slab_loc(3) = floor(slab_loc(3)/ct.resolution.z) + alignment(3);

% bulding the mask for where the slab is
mask = zeros(ct.cubeDim);
    
for i = -geo(1):geo(1)
    for j = -2 * geo(2) : 0
        for z = -geo(3):geo(3)
            ix = slab_loc + [i, j, z];
            mask(ix(1),ix(2),ix(3)) = 1;
        end
    end
end

% assigning electron density to the slab
ct.cube{1}(mask == 1) = vars.slab_ed;
ct.cubeHU{1}(mask == 1) = vars.slab_hu;

stf = matRad_generateStf(ct, cst, pln);
stf.ray.energy = vars.Energy;

dij = matRad_calcParticleDose(ct,stf,pln,cst);

resultGUI = matRad_fluenceOptimization(dij,cst,pln);

end

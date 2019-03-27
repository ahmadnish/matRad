function dij = matRad_calcParticleDose(ct,stf,pln,cst)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% matRad particle dose calculation wrapper
% 
% call
%   dij = matRad_calcParticleDose(ct,stf,pln,cst)
%
% input
%   ct:             ct cube
%   stf:            matRad steering information struct
%   pln:            matRad plan meta information struct
%   cst:            matRad cst struct
%   calcDoseDirect: boolian switch to bypass dose influence matrix
%                   computation and directly calculate dose; only makes
%                   sense in combination with matRad_calcDoseDirect.m
%
% output
%   dij:            matRad dij struct
%
% References
%   [1] http://iopscience.iop.org/0031-9155/41/8/005
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% Copyright 2015 the matRad development team. 
% 
% This file is part of the matRad project. It is subject to the license 
% terms in the LICENSE file found in the top-level directory of this 
% distribution and at https://github.com/e0404/matRad/LICENSES.txt. No part 
% of the matRad project, including this file, may be copied, modified, 
% propagated, or distributed except according to the terms contained in the 
% LICENSE file.
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% calculate rED or rSP from HU
ct = matRad_calcWaterEqD(ct, pln);

% meta information for dij
dij.numOfBeams         = pln.propStf.numOfBeams;
dij.numOfVoxels        = prod(ct.cubeDim);
dij.resolution         = ct.resolution;
dij.dimensions         = ct.cubeDim;
dij.numOfScenarios     = 1;
dij.numOfRaysPerBeam   = [stf(:).numOfRays];
dij.totalNumOfBixels   = sum([stf(:).totalNumOfBixels]);
dij.totalNumOfRays     = sum(dij.numOfRaysPerBeam);

% Only take voxels inside patient.
V = [cst{:,4}];
V = unique(vertcat(V{:}));

% ignore densities outside of contours
eraseCtDensMask = ones(dij.numOfVoxels,1);
eraseCtDensMask(V) = 0;
for i = 1:ct.numOfCtScen
    ct.cube{i}(eraseCtDensMask == 1) = 0;
end

% Convert CT subscripts to linear indices.
[yCoordsV_vox, xCoordsV_vox, zCoordsV_vox] = ind2sub(ct.cubeDim,V);

% load machine file
fileName = [pln.radiationMode '_' pln.machine];
try
   load([fileparts(mfilename('fullpath')) filesep fileName]);
catch
   error(['Could not find the following machine file: ' fileName ]); 
end

if isfield(pln,'propDoseCalc') && ...
   isfield(pln.propDoseCalc,'calcLET') && ...
   pln.propDoseCalc.calcLET
  if isfield(machine.data,'LET')
    letDoseTmpContainer = cell(numOfBixelsContainer,dij.numOfScenarios);
    % Allocate space for dij.dosexLET sparse matrix
    for i = 1:dij.numOfScenarios
        dij.mLETDose{i} = spalloc(prod(ct.cubeDim),numOfColumnsDij,1);
    end
  else
    warndlg('LET not available in the machine data. LET will not be calculated.');
  end
end

% generates tissue class matrix for biological optimization
if (isequal(pln.propOpt.bioOptimization,'LEMIV_effect') || isequal(pln.propOpt.bioOptimization,'LEMIV_RBExD')) ... 
        && strcmp(pln.radiationMode,'carbon')
    
    fprintf('matRad: loading biological base data... ');
    vTissueIndex = zeros(size(V,1),1);
    
    %set overlap priorities
    cst  = matRad_setOverlapPriorities(cst);
    
    for i = 1:size(cst,1)
        % find indices of structures related to V
        [~, row] = ismember(vertcat(cst{i,4}{:}),V,'rows'); 
        % check if base data contains alphaX and betaX
        if   isfield(machine.data,'alphaX') && isfield(machine.data,'betaX')
            % check if cst is compatiable 
            if ~isempty(cst{i,5}) && isfield(cst{i,5},'alphaX') && isfield(cst{i,5},'betaX') 

                IdxTissue = find(ismember(machine.data(1).alphaX,cst{i,5}.alphaX) & ...
                                 ismember(machine.data(1).betaX,cst{i,5}.betaX));

                % check consitency of biological baseData and cst settings
                if ~isempty(IdxTissue)
                    vTissueIndex(row) = IdxTissue;
                else
                    error('biological base data and cst inconsistent\n');
                end
            else
                vTissueIndex(row) = 1;
                fprintf(['matRad: tissue type of ' cst{i,2} ' was set to 1 \n']);
            end
        else
            error('base data is incomplement - alphaX and/or betaX is missing');
        end
        
    end
    fprintf('done.\n');

% issue warning if biological optimization not possible
elseif sum(strcmp(pln.propOpt.bioOptimization,{'LEMIV_effect','LEMIV_RBExD'}))>0 && ~strcmp(pln.radiationMode,'carbon') ||...
       ~strcmp(pln.radiationMode,'protons') && strcmp(pln.propOpt.bioOptimization,'const_RBExD')
    warndlg([pln.propOpt.bioOptimization ' optimization not possible with ' pln.radiationMode '- physical optimization is carried out instead.']);
    pln.propOpt.bioOptimization = 'none';      
end

% compute SSDs
stf = matRad_computeSSD(stf,ct);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
for i = 1:length(stf) % loop over all beams
    
    fprintf(['Beam ' num2str(i) ' of ' num2str(length(stf)) ': \n']);
            
    % convert voxel indices to real coordinates using iso center of beam i
    xCoordsV = xCoordsV_vox(:)*ct.resolution.x-stf(i).isoCenter(1);
    yCoordsV = yCoordsV_vox(:)*ct.resolution.y-stf(i).isoCenter(2);
    zCoordsV = zCoordsV_vox(:)*ct.resolution.z-stf(i).isoCenter(3);
    coordsV  = [xCoordsV yCoordsV zCoordsV];

    % Get Rotation Matrix
    % Do not transpose matrix since we usage of row vectors &
    % transformation of the coordinate system need double transpose

    % rotation around Z axis (gantry)
    rotMat_system_T = matRad_getRotationMatrix(stf(i).gantryAngle,stf(i).couchAngle);

    % Rotate coordinates (1st couch around Y axis, 2nd gantry movement)
    rot_coordsV = coordsV*rotMat_system_T;

    rot_coordsV(:,1) = rot_coordsV(:,1)-stf(i).sourcePoint_bev(1);
    rot_coordsV(:,2) = rot_coordsV(:,2)-stf(i).sourcePoint_bev(2);
    rot_coordsV(:,3) = rot_coordsV(:,3)-stf(i).sourcePoint_bev(3);

    % Calcualte radiological depth cube
    lateralCutoffRayTracing = 50;
    fprintf('matRad: calculate radiological depth cube...');
    radDepthV = matRad_rayTracingXXX(stf(i),ct,V,rot_coordsV,lateralCutoffRayTracing);
    fprintf('done.\n');
    
    % get indices of voxels where ray tracing results are available
    radDepthIx = find(~isnan(radDepthV{1}));
    
    % limit rotated coordinates to positions where ray tracing is availabe
    rot_coordsV = rot_coordsV(radDepthIx,:);
    
end

    
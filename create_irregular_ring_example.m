function [cst, structInfo] = create_irregular_ring_example(ct, cst, refStructureIdx, varargin)
% Create irregular margin structure (ring, expansion, or shrinkage)
%
% Input:
%   ct               - CT structure
%   cst              - Clinical structure template
%   refStructureIdx  - Index of reference structure in CST
%   varargin         - Optional parameters:
%                      'margins', struct('x',5,'y',5,'z',5) - margins in mm (default: 5mm isotropic)
%                      'operation', 'ring'|'expand'|'shrink' - operation type (default: 'ring')
%
% Output:
%   cst              - Updated CST with new structure
%   structInfo       - Information about created structure

% Parse input arguments
p = inputParser;
addRequired(p, 'ct');
addRequired(p, 'cst');
addRequired(p, 'refStructureIdx', @(x) isnumeric(x) && x > 0 && x <= size(cst,1));
addParameter(p, 'margins', struct('x', 5, 'y', 5, 'z', 5), @isstruct);
addParameter(p, 'operation', 'ring', @(x) ismember(x, {'ring', 'expand', 'shrink'}));
parse(p, ct, cst, refStructureIdx, varargin{:});

irregularMargin = p.Results.margins;
operation = p.Results.operation;

% Validate reference structure index
if refStructureIdx < 1 || refStructureIdx > size(cst,1)
    error('Reference structure index %d is out of range [1, %d]', refStructureIdx, size(cst,1));
end

% Get reference structure info
refStructureName = cst{refStructureIdx,2};
refIndices = cst{refStructureIdx,4}{1};
refMask = false(ct.cubeDim);
refMask(refIndices) = true;

% Generate structure name based on margins and operation
marginStr = generate_margin_string(irregularMargin);
operationStr = get_operation_suffix(operation);
newStructureName = sprintf('%s%s%s', refStructureName, marginStr, operationStr);

% Perform the requested operation
switch operation
    case 'expand'
        % Simple expansion
        newMask = matRad_addMargin(refMask, cst, ct.resolution, irregularMargin, true);
        
    case 'shrink'
        % Shrinkage: expand the complement, then take complement
        complementMask = ~refMask;
        expandedComplement = matRad_addMargin(complementMask, cst, ct.resolution, irregularMargin, true);
        newMask = ~expandedComplement & refMask;
        
    case 'ring'
        % Ring: expansion minus original
        expandedMask = matRad_addMargin(refMask, cst, ct.resolution, irregularMargin, true);
        newMask = expandedMask & ~refMask;
        
    otherwise
        error('Unknown operation: %s', operation);
end

newIndices = find(newMask);

% Add new structure to CST
newRow = size(cst,1) + 1;

cst{newRow, 1} = newRow;                    % Index
cst{newRow, 2} = newStructureName;          % Name  
cst{newRow, 3} = determine_structure_type(operation, cst{refStructureIdx,3}); % Type
cst{newRow, 4} = {newIndices};              % Voxel indices
cst{newRow, 5}.Priority = 3;                % Priority
cst{newRow, 5}.visibleColor = rand(1,3);    % Random RGB color
cst{newRow, 5}.Visible = 1;                 % Make visible

% Create structure info
structInfo.name = newStructureName;
structInfo.referenceStructure = refStructureName;
structInfo.referenceIndex = refStructureIdx;
structInfo.operation = operation;
structInfo.margins_mm = irregularMargin;
structInfo.voxelsAdded = numel(newIndices);
structInfo.mask = newMask;

% Display summary
fprintf('\n=== Structure Creation Summary ===\n');
fprintf('Reference structure: %s (index %d)\n', refStructureName, refStructureIdx);
fprintf('New structure: %s\n', newStructureName);
fprintf('Operation: %s\n', operation);
fprintf('Margins: X=%.1fmm, Y=%.1fmm, Z=%.1fmm\n', ...
    irregularMargin.x, irregularMargin.y, irregularMargin.z);
fprintf('Voxels in new structure: %d\n', structInfo.voxelsAdded);
fprintf('CT resolution: [%.2f %.2f %.2f] mm\n', ...
    ct.resolution.x, ct.resolution.y, ct.resolution.z);

% Calculate actual voxel margins for verification
voxelMargins = [irregularMargin.x/ct.resolution.x, ...
                irregularMargin.y/ct.resolution.y, ...
                irregularMargin.z/ct.resolution.z];
fprintf('Voxel margins: [%.1f %.1f %.1f] voxels\n', voxelMargins);
fprintf('==================================\n\n');

end

% Helper functions
function marginStr = generate_margin_string(margins)
    % Generate margin string for structure name
    if margins.x == margins.y && margins.y == margins.z
        % Isotropic margins
        marginStr = sprintf('_%dmm', margins.x);
    else
        % Anisotropic margins
        marginStr = sprintf('_%dx%dx%d', margins.x, margins.y, margins.z);
    end
end

function suffix = get_operation_suffix(operation)
    % Get suffix for operation type
    switch operation
        case 'ring'
            suffix = '_ring';
        case 'expand'
            suffix = '_expnd';
        case 'shrink'
            suffix = '_shrink';
        otherwise
            suffix = '';
    end
end

function structType = determine_structure_type(operation, refType)
    % Determine appropriate structure type based on operation
    switch operation
        case 'ring'
            structType = 'OAR';  % Rings are typically OARs for dose constraints
        case 'expand'
            structType = refType; % Expanded structure keeps original type
        case 'shrink'
            structType = refType; % Shrunken structure keeps original type
        otherwise
            structType = 'OAR';
    end
end

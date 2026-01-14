classdef matRad_QuarticOverdosing < DoseObjectives.matRad_DoseObjective
% matRad_QuarticOverdosing Implements a penalized quartic (4th power) overdosing objective
%   This objective penalizes overdosing with a 4th power penalty, providing
%   stronger suppression of hot spots compared to squared overdosing.
%   See matRad_DoseObjective for interface description
%
% References
%   -
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% Copyright 2020 the matRad development team. 
% 
% This file is part of the matRad project. It is subject to the license 
% terms in the LICENSE file found in the top-level directory of this 
% distribution and at https://github.com/e0404/matRad/LICENSE.md. No part 
% of the matRad project, including this file, may be copied, modified, 
% propagated, or distributed except according to the terms contained in the 
% LICENSE file.
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    properties (Constant)
        name = 'Quartic Overdosing';
        parameterNames = {'d^{max}'};
        parameterTypes = {'dose'};
    end
    
    properties
        parameters = {30};
        penalty = 1;
    end
    
    methods
        function obj = matRad_QuarticOverdosing(penalty,dMax)
            %If we have a struct in first argument
            if nargin == 1 && isstruct(penalty)
                inputStruct = penalty;
                initFromStruct = true;
            else
                initFromStruct = false;
                inputStruct = [];
            end
            
            %Call Superclass Constructor (for struct initialization)
            obj@DoseObjectives.matRad_DoseObjective(inputStruct);
            
            %now handle initialization from other parameters
            if ~initFromStruct
                if nargin == 2 && isscalar(dMax)
                    obj.parameters{1} = dMax;
                end
                
                if nargin >= 1 && isscalar(penalty)
                    obj.penalty = penalty;
                end
            end
        end
        
        %% Calculates the Objective Function value
        function fDose = computeDoseObjectiveFunction(obj,dose)
            % overdose : dose minus prefered dose
            overdose = dose - obj.parameters{1};
            
            % apply positive operator
            overdose(overdose<0) = 0;
            
            % calculate quartic objective function (4th power)
            fDose = 1/numel(dose) * sum(overdose.^4);
        end
        
        %% Calculates the Objective Function gradient
        function fDoseGrad   = computeDoseObjectiveGradient(obj,dose)
            % overdose : dose minus prefered dose
            overdose = dose - obj.parameters{1};
            
            % apply positive operator
            overdose(overdose<0) = 0;
            
            % calculate gradient (4 * overdose^3)
            fDoseGrad = 4 * 1/numel(dose) * (overdose.^3);
        end
    end
    
end
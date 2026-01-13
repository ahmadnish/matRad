function cst = untick_all(cst, varargin)
    % UNTICK_ALL - Hide all CST structures except specified ones
    %
    % Usage:
    %   cst = untick_all(cst, 'except', 'Skin')                    % Keep only 'Skin' visible
    %   cst = untick_all(cst, 'except', {'Skin', 'Brain_stem'})    % Keep multiple structures visible
    %   cst = untick_all(cst, 'except', [1, 3, 5])                % Keep structures by index visible
    %   cst = untick_all(cst, 'except', {1, 'Skin', 3})           % Mixed indices and names
    %
    % Inputs:
    %   cst    - matRad CST cell array
    %   except - Structure name(s) or index/indices to keep visible
    %
    % Output:
    %   cst    - Modified CST with updated visibility
    
    % Parse input arguments
    p = inputParser;
    addRequired(p, 'cst', @iscell);
    addParameter(p, 'except', {}, @(x) ischar(x) || iscellstr(x) || isnumeric(x) || iscell(x));
    parse(p, cst, varargin{:});
    
    except = p.Results.except;
    
    % Convert single inputs to cell arrays for uniform processing
    if ischar(except)
        except = {except};
    elseif isnumeric(except)
        except = num2cell(except);
    end
    
    % First, hide all structures
    for i = 1:size(cst, 1)
        if ~isempty(cst{i,5})
            cst{i,5}.Visible = 0;
        end
    end
    
    % Then, show only the specified structures
    for i = 1:length(except)
        item = except{i};
        
        if isnumeric(item)
            % Handle numeric index
            idx = item;
            if idx >= 1 && idx <= size(cst, 1) && ~isempty(cst{idx,5})
                cst{idx,5}.Visible = 1;
            end
        elseif ischar(item)
            % Handle structure name
            for j = 1:size(cst, 1)
                if strcmp(cst{j,2}, item) && ~isempty(cst{j,5})
                    cst{j,5}.Visible = 1;
                    break;
                end
            end
        end
    end
    
    end
function mask = slabGeometry(vars, cubeDim)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% takes the shape and the size of the geometry and produces the
% corresponding mask cube for it.
%
%   call:
%         mask = slabGeometry(vars, cubeDim)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
shape = vars.geo.shape;
geo = vars.geo.size;
slab_loc = vars.slab_loc;

mask = zeros(cubeDim);

switch shape
    
    case 'Rectangle'
        
        for i = -geo(1):geo(1)
            for j = -geo(2) : geo(2)
                for k = -geo(3):geo(3)
                    ix = slab_loc + [i, j, k];
                    mask(ix(1),ix(2),ix(3)) = 1;
                end
            end
        end
        
    case 'Ellipsoid'
        
        for i = -geo(1):geo(1)
            for j = -geo(2):geo(2)
                for k = -geo(3):geo(3)
                    ix = slab_loc + [i,j,k];
                    if (sum(([i,j,k].^2) ./ (geo.^2)) <= 1)
                        mask(ix(1),ix(2),ix(3)) = 1;
                    end                       
                end
            end
        end

    case 'Pyramid'
        
        for i = 0:geo(1)
            for j = 0:geo(2)
                for k = 0:geo(3)
                    ix = slab_loc + [i,j,k];
                    if (i <= ((1 - j/geo(2)) * geo(1)) && k <= (1 - j/geo(2)) * geo(3))
                        mask(ix(1),ix(2),ix(3)) = 1;
                    end                       
                end
            end
        end
        
    otherwise
        
            error('the slab geometry is not defined')
            
end

% 
%     center = slab_loc - [0 round(geo(2)/2) 0];
%                     currPos = center + [i j z];
                             
end
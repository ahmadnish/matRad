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
    
    case 'Rec'
        
        for i = -geo(1):geo(1)
            for j = -2 * geo(2) : 0
                for z = -geo(3):geo(3)
                    ix = slab_loc + [i, j, z];
                    mask(ix(1),ix(2),ix(3)) = 1;
                end
            end
        end
        
    otherwise
        
            error('the slab geometry is not defined')
            
end


            
end
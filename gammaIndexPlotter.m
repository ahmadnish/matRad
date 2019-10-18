function [gammaCube, pass] = gammaIndexPlotter(ct, dose, dose_ann, plotting, slices, criteria, dim)


% if ~exist('', 'var') || isempty(), = ;end
if ~exist('plotting', 'var') || isempty(plotting), plotting = true; end
if ~exist('slices', 'var') || isempty(slices), slices = floor(size(ct, 2)/2) + 1; end
if ~exist('criteria', 'var') || isempty(criteria), criteria = [.5 1]; end
if ~exist('dim', 'var') || isempty(dim), dim = true; end


dose = dose/1000;
dose = dose * 1.992;

dose_ann = dose_ann/1000;
dose_ann = dose_ann * 1.992;

[gammaCube] = matRad_gammaIndex(dose,dose_ann,[2 2 2], criteria, [], 3);

pass = 100 - ((nnz(gammaCube>1) * 100 )/(nnz(gammaCube>0)));


if plotting    

    
    figure
    set(gcf, 'Units', 'Normalized', 'OuterPosition', [0.3, 0.3, .5, .7]);
    
    combined = [dose dose_ann];
    mAx = max(combined(:));
    mIN = min(combined(:));
    
    tmp = unique([ct(:, 1, :) ct(:,end,:)]);
    
    if length(tmp) ~= 1 && dim
    

        for i = slices
            ax = subplot(141);
            imagesc(squeeze(ct(:,:,i)))
            title('CT (RSP)')
            colorbar()
            colormap(gca, 'gray')
            caxis(ax, [0, 2.5])
            set(gca, 'FontSize', 16, 'FontName', 'FixedWidth', 'FontWeight', 'bold')
            ylabel('y [mm]')
            xlabel('x [mm]')
            ax1 = subplot(142);
            imagesc(squeeze(dose(:,:,i)))
            colorbar()
            colormap(gca, 'jet')
            title({'MC [Gy]', ['ID = ', num2str(sum(dose(:)), '%.4f'), ' Gy']})
            xlabel('x [mm]')
            set(gca, 'FontSize', 16, 'FontName', 'FixedWidth', 'FontWeight', 'bold')
            ax2 = subplot(143);
            imagesc(squeeze(dose_ann(:,:,i)))
            title({'ANN [Gy]', ['ID = ', num2str(sum(dose_ann(:)), '%.4f'), ' Gy']})
            colorbar()
            colormap(gca, 'jet')
            xlabel('x [mm]')

            caxis(ax1, [mIN, mAx])
            caxis(ax2, [mIN, mAx])
            set(gca, 'FontSize', 16, 'FontName', 'FixedWidth', 'FontWeight', 'bold')
            subplot(144)
            imagesc(squeeze(gammaCube(:, :, i)))
            title({'[\gamma]', ['PR = ', num2str(pass) ' %']})
            caxis([0 2]), colormap(gca, matRad_getColormap('gammaIndex')), colorbar
            xlabel('x [mm]')
            set(gca, 'FontSize', 16, 'FontName', 'FixedWidth', 'FontWeight', 'bold')
            pause(1)
            
        end
        
    else
        
        for i = slices
            ax = subplot(141);
            imagesc(squeeze(ct(:,i,:)))
            title('CT (RSP)')
            colorbar()
            colormap(gca, 'gray')
            caxis(ax, [0, 2.5])
            set(gca, 'FontSize', 16, 'FontName', 'FixedWidth', 'FontWeight', 'bold')
            ylabel('y [mm]')
            xlabel('x [mm]')
            ax1 = subplot(142);
            imagesc(squeeze(dose(:,i,:)))
            colorbar()
            colormap(gca, 'jet')
            title({'MC [Gy]', ['ID = ', num2str(sum(dose(:)), '%.4f'), ' Gy']})
            set(gca, 'FontSize', 16, 'FontName', 'FixedWidth', 'FontWeight', 'bold')
            xlabel('x [mm]')
            ax2 = subplot(143);
            imagesc(squeeze(dose_ann(:,i,:)))
            title({'ANN [Gy]', ['ID = ', num2str(sum(dose_ann(:)), '%.4f'), ' Gy']})
            colorbar()
            colormap(gca, 'jet')
            
            caxis(ax1, [mIN, mAx])
            caxis(ax2, [mIN, mAx])
            set(gca, 'FontSize', 16, 'FontName', 'FixedWidth', 'FontWeight', 'bold')
            xlabel('x [mm]')
            subplot(144)
            imagesc(squeeze(gammaCube(:, i,:)))
            title({'[\gamma]', ['PR = ', num2str(pass) ' %']})
            caxis([0 2]), colormap(gca, matRad_getColormap('gammaIndex')), colorbar
            xlabel('x [mm]')
            set(gca, 'FontSize', 16, 'FontName', 'FixedWidth', 'FontWeight', 'bold')
            pause(1)
        end
        
    end
    
  

end

end


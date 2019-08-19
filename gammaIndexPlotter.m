function [gammaCube, pass] = gammaIndexPlotter(ct, dose, dose_ann, plotting, slices, criteria)

if plotting & ~exist('slices', 'var')
    slices = floor(size(ct, 2)/2) + 1;
end


if nargin < 5
    criteria = [1 2];
end


dose = dose/1000;
dose = dose * 1.992;

dose_ann = dose_ann/1000;
dose_ann = dose_ann * 1.992;

[gammaCube] = matRad_gammaIndex(dose,dose_ann,[2 2 2], criteria, [], 3);

pass = 100 - ((nnz(gammaCube>1) * 100 )/(nnz(gammaCube>0)));


if plotting    

    
    figure
    set(gcf, 'Units', 'Normalized', 'OuterPosition', [0, 0.3, .8, .7]);
    
    combined = [dose dose_ann];
    mAx = max(combined(:));
    mIN = min(combined(:));
    
    tmp = unique([ct(:, 1, :) ct(:,end,:)]);
    
    if length(tmp) ~= 1
    

        for i = slices
            ax = subplot(141);
            imagesc(squeeze(ct(:,:,i)))
            title('CT input (RSP)')
            colorbar()
            colormap(gca, 'gray')
            caxis(ax, [0, 2.5])

            ax1 = subplot(142);
            imagesc(squeeze(dose(:,:,i)))
            colorbar()
            colormap(gca, 'jet')
            title({'Monte Carlo Simulation [Gy]', ['Integral Dose = ', num2str(sum(dose(:)), '%.4f'), ' Gy']})
            ax2 = subplot(143);
            imagesc(squeeze(dose_ann(:,:,i)))
            title({'Estimated dose by ANN [Gy]', ['Integral Dose = ', num2str(sum(dose_ann(:)), '%.4f'), ' Gy']})
            colorbar()
            colormap(gca, 'jet')

            caxis(ax1, [mIN, mAx])
            caxis(ax2, [mIN, mAx])

            subplot(144)
            imagesc(squeeze(gammaCube(:, :, i)))
            title({'Gamma index analysis [\gamma]', ['Pass rate = ', num2str(pass) ' %']})
            caxis([0 2]), colormap(gca, matRad_getColormap('gammaIndex')), colorbar

            pause(1)
        end
        
    else
        
        for i = slices
            ax = subplot(411);
            imagesc(squeeze(ct(:,i,:))')
            title('CT input (RSP)')
            colorbar()
            colormap(gca, 'gray')
            caxis(ax, [0, 2.5])

            ax1 = subplot(412);
            imagesc(squeeze(dose(:,i,:))')
            colorbar()
            colormap(gca, 'jet')
            title(['Monte Carlo Simulation [Gy] - Integral Dose = ', num2str(sum(dose(:)), '%.4f'), ' Gy'])
            ax2 = subplot(413);
            imagesc(squeeze(dose_ann(:,i,:))')
            title(['Estimated dose by ANN [Gy] - Integral Dose = ', num2str(sum(dose_ann(:)), '%.4f'), ' Gy'])
            colorbar()
            colormap(gca, 'jet')

            caxis(ax1, [mIN, mAx])
            caxis(ax2, [mIN, mAx])

            subplot(414)
            imagesc(squeeze(gammaCube(:, i,:))')
            title(['Gamma index analysis [\gamma] - Pass rate = ', num2str(pass) ' %'])
            caxis([0 2]), colormap(gca, matRad_getColormap('gammaIndex')), colorbar

            pause(1)
        end
        
    end
    
  

end

end


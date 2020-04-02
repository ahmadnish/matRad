function [gammaCube, pass] = gammaIndexPlotter_h(ct, dose, dose_ann, plotting, slices, criteria, dim)


% if ~exist('', 'var') || isempty(), = ;end
if ~exist('plotting', 'var') || isempty(plotting), plotting = true; end
if ~exist('slices', 'var') || isempty(slices), slices = floor(size(ct, 2)/2) + 1; end
if ~exist('criteria', 'var') || isempty(criteria), criteria = [.5 1]; end
if ~exist('dim', 'var') || isempty(dim), dim = true; end

scaleLabelX = 1.1;

dose = dose/1000;
dose = dose * 1.992;

dose_ann = dose_ann/1000;
dose_ann = dose_ann * 1.992;

[gammaCube] = matRad_gammaIndex(dose,dose_ann,[2 2 2], criteria, [], 3);

pass = (1 - nnz(gammaCube>1)/ nnz(gammaCube>0)) * 100;

if size(dose,1) == size(dose, 1)
    tickdistX = 12.5; tickdistY = 5;
    XXtick = [0 : tickdistX : size(ct, 1)];
    YYtick = [0 : tickdistY : size(ct, 2)];
else
    warning('sizes of CT and Dose are not the same, axis labels might be not accurate!')
end


if plotting    

    figure
    set(gcf, 'Color', 'w');
    set(gcf, 'Units', 'Normalized', 'OuterPosition', [0.3, 0.3, .5, .7]);
    set(gcf, 'Units', 'Normalized', 'OuterPosition', [0, 0, .5, 1]);
    combined = [dose dose_ann];
    mAx = max(combined(:));
    mIN = min(combined(:));
    
    for i = slices
        
        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% subplot 1
        ax = subplot(411);
        imagesc(squeeze(ct(:,:,i))')

        %title('CT (RSP)')
        
        % colorbar
        hcb = colorbar();
        colormap(gca, 'gray')
        caxis(ax, [0, 2.5])
        ylabel(hcb, 'RSP', 'FontName', 'Liberation Serif', 'FontSize', 12, 'FontWeight', 'bold')

        % ticks
        ticker(gca, 2, XXtick, YYtick)
        
        % axis labels
        Xlm = xlim; Ylm = ylim;      
        xlabel('mm', 'Position', [Xlm(2), scaleLabelX * Ylm(2)], 'FontName', 'Liberation Serif', 'FontSize', 12)
        ylabel('mm', 'Position', [0, scaleLabelX * Ylm(1)], 'FontName', 'Liberation Serif', 'FontSize', 12)
        
        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% subplot 2
        ax1 = subplot(412);
        imagesc(squeeze(dose(:,:,i))')
        %title({'MC [Gy]', ['ID = ', num2str(sum(dose(:)), '%.4f'), ' Gy']})
        
        % colorbar
        hcb = colorbar();
        colormap(gca, 'jet')
        ylabel(hcb, 'Dose [Gy]', 'FontName', 'Liberation Serif', 'FontSize', 12, 'FontWeight', 'bold')
        
        % ticks
        ticker(gca, 2, XXtick, YYtick)
        
        % axis labels
        Xlm = xlim; Ylm = ylim;
        xlabel('mm', 'Position', [Xlm(2), scaleLabelX * Ylm(2)], 'FontName', 'Liberation Serif', 'FontSize', 12)
        ylabel('mm', 'Position', [0, scaleLabelX * Ylm(1)], 'FontName', 'Liberation Serif', 'FontSize', 12)
        
        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% subplot 3
        ax2 = subplot(413);
        imagesc(squeeze(dose_ann(:,:,i))')
        %title({'ANN [Gy]', ['ID = ', num2str(sum(dose_ann(:)), '%.4f'), ' Gy']})
        
        % colorbar
        hcb = colorbar();
        colormap(gca, 'jet')
        caxis(ax1, [mIN, mAx])
        caxis(ax2, [mIN, mAx])
        ylabel(hcb, 'Dose [Gy]', 'FontName', 'Liberation Serif', 'FontSize', 12, 'FontWeight', 'bold')
        %ticks
        ticker(gca, 2, XXtick, YYtick)
        
        % axis labels
        Xlm = xlim; Ylm = ylim;
        ylabel('mm', 'Position', [0, scaleLabelX * Ylm(1)], 'FontName', 'Liberation Serif', 'FontSize', 12)
        xlabel('mm', 'Position', [Xlm(2), scaleLabelX * Ylm(2)], 'FontName', 'Liberation Serif', 'FontSize', 12)
        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% subplot 4
        subplot(414)
        imagesc(squeeze(gammaCube(:, :, i))')
        %title({'[\gamma]', ['PR = ', num2str(pass) ' %']})
        
        % colorbar
        caxis([0 2]), colormap(gca, matRad_getColormap('gammaIndex'))
        hcb = colorbar;
        ylabel(hcb, '\gamma value', 'FontName', 'Liberation Serif', 'FontSize', 12, 'FontWeight', 'bold')
        
        % ticks
        ticker(gca, 2, XXtick, YYtick)
        
        % axis labels
        Xlm = xlim; Ylm = ylim;
        xlabel('mm', 'Position', [Xlm(2), scaleLabelX * Ylm(2)], 'FontName', 'Liberation Serif', 'FontSize', 12)
        ylabel('mm', 'Position', [0, scaleLabelX * Ylm(1)], 'FontName', 'Liberation Serif', 'FontSize', 12)
%                 
        pause(1)

    end   
    
end
    

end


function ticker(h, scaling, xticks, yticks)

set(h, 'FontSize', 12, 'FontName', 'Liberation Serif')

set(h, 'XTick', xticks)
set(h, 'YTick', yticks)
set(h, 'XTickLabel', xticks*scaling)
set(h, 'YTickLabel', yticks*scaling)

end
function statusAll = runMatRadTests(varargin)
%% This file runs the complete matRad test suite.


CI_MODE = strcmpi(getenv('CONTINUOUS_INTEGRATION'),'true') || strcmp(getenv('CI'),'true');
isJenkins = ~isempty(getenv('JENKINS_URL'));

%% Set path
addpath(fullfile(pwd,'suites'));
addpath(fullfile(pwd,'..'));
addpath(fullfile(pwd,'..','examples'));

%% Select functions to runs
suite = @coreTest;
allTests = 1:numel(suite(0));

%% Prepare environment
if strcmpi(getEnvironment(), 'Octave')
  % Ensure that paging is disabled
  % https://www.gnu.org/software/octave/doc/interpreter/Paging-Screen-Output.html
  more off
end

%% Run tests
status = coreTest(1);

matRad_example5_protons

%% Calculate exit code
if CI_MODE
    exit(nErrors);
end

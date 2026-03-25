# /usr/src/redmine/config/initializers/coverage_helper.rb
$VERBOSE = nil

# Try to require simplecov if possible
begin
  require 'simplecov'
rescue LoadError
  puts "Could not load simplecov gem"
end

# Only start coverage if the gem is loaded
if defined?(SimpleCov)
  SimpleCov.command_name 'API Integration Tests'
  SimpleCov.start 'rails' do
    coverage_dir '/usr/src/redmine/coverage'
    track_files 'app/**/*.rb'
    add_filter '/test/'
    add_filter '/config/'
    add_filter '/vendor/'
    add_group 'Controllers', 'app/controllers'
    add_group 'Models', 'app/models'
    add_group 'Helpers', 'app/helpers'
    add_group 'Mailers', 'app/mailers'
    use_merging true
    merge_timeout 3600
  end
  puts "SimpleCov started successfully! Report will be in /usr/src/redmine/coverage"
else
  puts "SimpleCov not defined. Coverage will not be tracked."
end

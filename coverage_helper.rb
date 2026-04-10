$VERBOSE = nil

begin
  require 'simplecov'
rescue LoadError
  puts "Could not load simplecov gem"
end

if defined?(SimpleCov)
  SimpleCov.command_name "worker-#{Process.pid}"
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

  # Save coverage after every 10th request
  $request_count = 0
  ActiveSupport::Notifications.subscribe('process_action.action_controller') do |*args|
    $request_count += 1
    if $request_count % 1 == 0
      SimpleCov.result.format!
    end
  end

  puts "SimpleCov started successfully! PID: #{Process.pid}"
else
  puts "SimpleCov not defined. Coverage will not be tracked."
end

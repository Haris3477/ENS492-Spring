$VERBOSE = nil

begin
  $LOAD_PATH.unshift '/app/vendor/bundle/ruby/3.4.0/gems/simplecov-0.22.0/lib'
  $LOAD_PATH.unshift '/app/vendor/bundle/ruby/3.4.0/gems/simplecov-html-0.13.2/lib'
  $LOAD_PATH.unshift '/app/vendor/bundle/ruby/3.4.0/gems/docile-1.4.1/lib'
  $LOAD_PATH.unshift '/app/vendor/bundle/ruby/3.4.0/gems/simplecov_json_formatter-0.1.4/lib'
  load '/app/vendor/bundle/ruby/3.4.0/gems/simplecov-0.22.0/lib/simplecov.rb'
rescue => e
  puts "Could not load simplecov gem: #{e.message}"
end

if defined?(SimpleCov)
  SimpleCov.command_name "worker-#{Process.pid}"
  SimpleCov.start 'rails' do
    coverage_dir '/app/coverage'
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

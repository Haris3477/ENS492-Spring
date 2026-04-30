$VERBOSE = nil

begin
  require 'simplecov'
rescue LoadError
  puts "Could not load simplecov gem"
end

if defined?(SimpleCov)
  SimpleCov.start 'rails' do
    coverage_dir '/usr/src/redmine/coverage'
    command_name "redmine-api-tests-#{Process.pid}"
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

  class SimpleCovFlusherMiddleware
    @@mutex = Mutex.new
    @@worker_initialized = false

    def initialize(app)
      @app = app
    end

    def ensure_worker_coverage_started
      return if @@worker_initialized
      @@mutex.synchronize do
        return if @@worker_initialized
        require 'coverage'
        unless Coverage.running?
          begin
            Coverage.start(lines: true)
          rescue RuntimeError
            Coverage.resume if Coverage.respond_to?(:resume)
          end
        end
        @@worker_initialized = true
      end
    end

    def call(env)
      ensure_worker_coverage_started
      case env['PATH_INFO']
      when '/__cov_reset__'
        return reset_coverage
      when '/__cov_count__'
        return cov_count
      end
      @app.call(env)
    end

    def reset_coverage
      @@mutex.synchronize do
        begin
          require 'coverage'
          Coverage.result(stop: false, clear: true) if Coverage.running?
          SimpleCov.instance_variable_set(:@result, nil)
          File.unlink('/usr/src/redmine/coverage/.resultset.json') rescue nil
          File.unlink('/usr/src/redmine/coverage/.last_run.json') rescue nil
          File.unlink('/usr/src/redmine/coverage/.resultset.json.lock') rescue nil
          [200, { 'Content-Type' => 'text/plain' }, ["coverage reset OK pid=#{Process.pid}\n"]]
        rescue => e
          [500, { 'Content-Type' => 'text/plain' }, ["reset failed: #{e.class}: #{e.message}\n"]]
        end
      end
    end

    def cov_count
      begin
        require 'coverage'
        unless Coverage.running?
          return [200, { 'Content-Type' => 'text/plain' }, ["0 not_running pid=#{Process.pid}\n"]]
        end
        result = Coverage.peek_result
        count = 0
        result.each do |_file, file_data|
          lines = file_data.is_a?(Hash) ? file_data[:lines] : file_data
          next unless lines
          lines.each { |ln| count += 1 if ln.is_a?(Integer) && ln > 0 }
        end
        [200, { 'Content-Type' => 'text/plain' }, ["#{count}\n"]]
      rescue => e
        [500, { 'Content-Type' => 'text/plain' }, ["count failed: #{e.class}: #{e.message}\n"]]
      end
    end
  end

  if defined?(Rails)
    Rails.application.config.middleware.use SimpleCovFlusherMiddleware
    puts "SimpleCovFlusherMiddleware registered (Redmine)."
  end

  puts "SimpleCov started successfully! PID: #{Process.pid}"
else
  puts "SimpleCov not defined. Coverage will not be tracked."
end

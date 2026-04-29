$VERBOSE = nil

vendor_path = '/app/vendor/bundle/ruby/3.4.0'
Dir.glob("#{vendor_path}/gems/*/lib").each { |p| $LOAD_PATH.unshift(p) }

begin
  require 'simplecov'
rescue LoadError => e
  puts "Could not load simplecov gem: #{e.message}"
end

if defined?(SimpleCov)
  SimpleCov.start 'rails' do
    coverage_dir '/app/coverage'
    command_name "openproject-api-tests-#{Process.pid}"
    track_files 'app/**/*.rb'
    add_filter '/test/'
    add_filter '/spec/'
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
    @@last_flush = Time.now
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
          Coverage.start(lines: true)
          $stdout.write("[SimpleCovFlusher] Coverage.start re-armed in pid=#{Process.pid}\n") rescue nil
        end
        @@worker_initialized = true
      end
    end

    def call(env)
      ensure_worker_coverage_started
      if env['PATH_INFO'] == '/__cov_reset__'
        return reset_coverage
      end
      status, headers, body = @app.call(env)
      maybe_flush
      [status, headers, body]
    end

    def reset_coverage
      @@mutex.synchronize do
        begin
          require 'coverage'
          if Coverage.running?
            Coverage.result(stop: false, clear: true)
          end
          SimpleCov.instance_variable_set(:@result, nil)
          File.unlink('/app/coverage/.resultset.json') rescue nil
          File.unlink('/app/coverage/.last_run.json') rescue nil
          File.unlink('/app/coverage/.resultset.json.lock') rescue nil
          @@last_flush = Time.now
          [200, { 'Content-Type' => 'text/plain' }, ["coverage reset OK pid=#{Process.pid}\n"]]
        rescue => e
          [500, { 'Content-Type' => 'text/plain' }, ["reset failed: #{e.message}\n"]]
        end
      end
    end

    private

    def maybe_flush
      now = Time.now
      return if now - @@last_flush < 2
      @@mutex.synchronize do
        return if now - @@last_flush < 2
        begin
          SimpleCov.clear_result if SimpleCov.respond_to?(:clear_result)
          SimpleCov.instance_variable_set(:@result, nil)
          SimpleCov.result.format!
          @@last_flush = now
        rescue => e
          warn "SimpleCov flush failed: #{e.message}"
        end
      end
    end
  end

  if defined?(Rails)
    Rails.application.config.middleware.use SimpleCovFlusherMiddleware
    puts "SimpleCovFlusherMiddleware registered."
  end

  puts "SimpleCov started successfully! PID: #{Process.pid}"
else
  puts "SimpleCov not defined. Coverage will not be tracked."
end

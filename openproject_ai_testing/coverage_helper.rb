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
        was_running = Coverage.running?
        $stdout.write("[SimpleCovFlusher] init pid=#{Process.pid} was_running=#{was_running}\n") rescue nil
        unless was_running
          begin
            Coverage.start(lines: true)
          rescue RuntimeError => e
            $stdout.write("[SimpleCovFlusher] Coverage.start raised: #{e.message}\n") rescue nil
            Coverage.resume if Coverage.respond_to?(:resume)
          end
        end
        $stdout.write("[SimpleCovFlusher] init pid=#{Process.pid} now_running=#{Coverage.running?}\n") rescue nil
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
      status, headers, body = @app.call(env)
      # Skip periodic SimpleCov flush — it interferes with Coverage tracking
      # (calling SimpleCov.result.format! has been observed to flip Coverage.running? to false).
      # We don't need on-disk resultset for the line-weighted pass-rate metric.
      [status, headers, body]
    end

    def cov_count
      begin
        require 'coverage'
        running = Coverage.running?
        unless running
          return [200, { 'Content-Type' => 'text/plain' }, ["0 not_running pid=#{Process.pid}\n"]]
        end
        result = Coverage.peek_result
        count = 0
        files_seen = 0
        result.each do |_file, file_data|
          files_seen += 1
          lines = file_data.is_a?(Hash) ? file_data[:lines] : file_data
          next unless lines
          lines.each { |ln| count += 1 if ln.is_a?(Integer) && ln > 0 }
        end
        [200, { 'Content-Type' => 'text/plain' }, ["#{count}\n"]]
      rescue => e
        [500, { 'Content-Type' => 'text/plain' }, ["count failed: #{e.class}: #{e.message}\n"]]
      end
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
          # NOTE: do NOT call SimpleCov.clear_result — it stops Coverage tracking.
          # Just nil out the cached @result so SimpleCov.result rebuilds from a fresh peek_result.
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

"""
Performance Benchmark Testing
=============================

This script benchmarks the performance of the optimization functionality
to ensure that the new features don't negatively impact performance.

Benchmarks:
1. Tool execution timing - How fast each tool executes
2. Memory usage - Memory consumption during operations
3. Scalability - Performance with many optimization functions
4. Optimization convergence - Impact on optimization quality and speed
"""

import os
import sys
import time
import psutil
import json
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrad_tools import create_matrad_engine

class PerformanceBenchmark:
    """Performance benchmarking for optimization functionality."""
    
    def __init__(self):
        self.engine = create_matrad_engine()
        self.benchmarks = {}
        self.baseline_memory = 0
        
    def measure_memory(self):
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def benchmark_tool_execution(self):
        """Benchmark individual tool execution times."""
        print("\n" + "="*60)
        print("PERFORMANCE BENCHMARK: Tool Execution Times")
        print("="*60)
        
        # Setup
        self.engine.start_engine()
        self.engine.load_patient("HEAD_AND_NECK.mat")
        self.engine.create_empty_plan()
        self.engine.set_beam_angles([0, 72, 144])
        self.engine.generate_beam_geometry()
        self.engine.calculate_influence_matrix()
        
        timings = {}
        
        # Benchmark objective operations
        start_time = time.time()
        self.engine.add_optimization_objective("PTV70", "square_deviation", 70.0, 1000.0, rationale="Benchmark test")
        timings["add_objective"] = time.time() - start_time
        
        start_time = time.time()
        self.engine.get_current_objectives()
        timings["get_objectives"] = time.time() - start_time
        
        # Benchmark constraint operations
        start_time = time.time()
        self.engine.add_constraint("SPINAL_CORD", "min_max_dose", upper_bound=45.0, rationale="Benchmark test")
        timings["add_constraint"] = time.time() - start_time
        
        start_time = time.time()
        self.engine.get_current_constraints()
        timings["get_constraints"] = time.time() - start_time
        
        # Benchmark comprehensive inspection (new feature)
        start_time = time.time()
        self.engine.get_optimization_functions()
        timings["comprehensive_inspection"] = time.time() - start_time
        
        # Benchmark advanced parameters
        start_time = time.time()
        self.engine.add_optimization_objective(
            "PTV70", "eud", 70.0, 1000.0,
            eud_exponent=3.5, robustness="PROB",
            rationale="Advanced parameter benchmark"
        )
        timings["add_advanced_objective"] = time.time() - start_time
        
        self.benchmarks["tool_timings"] = timings
        
        # Print results
        print("Tool execution times:")
        for tool, timing in timings.items():
            print(f"  {tool}: {timing*1000:.1f} ms")
            
        return timings
    
    def benchmark_scalability(self):
        """Benchmark performance with many optimization functions."""
        print("\n" + "="*60)
        print("PERFORMANCE BENCHMARK: Scalability")
        print("="*60)
        
        structures = ["PTV70", "PTV63", "PAROTID_LT", "PAROTID_RT", "SPINAL_CORD", "BRAINSTEM", "MANDIBLE", "LARYNX"]
        scalability_results = {}
        
        # Test with increasing numbers of optimization functions
        for num_functions in [5, 10, 15, 20]:
            print(f"\nTesting with {num_functions} optimization functions...")
            
            # Clear existing functions
            for struct in structures:
                try:
                    self.engine.clear_all_objectives(struct)
                except:
                    pass
            
            # Add optimization functions
            start_time = time.time()
            memory_start = self.measure_memory()
            
            for i in range(num_functions):
                struct = structures[i % len(structures)]
                if i % 2 == 0:
                    # Add objective
                    self.engine.add_optimization_objective(
                        struct, "max_dose", 50.0, 1000.0,
                        rationale=f"Scalability test {i}"
                    )
                else:
                    # Add constraint
                    self.engine.add_constraint(
                        struct, "min_max_dose", upper_bound=75.0,
                        rationale=f"Scalability test {i}"
                    )
            
            setup_time = time.time() - start_time
            
            # Test inspection performance
            start_time = time.time()
            result = self.engine.get_optimization_functions()
            inspection_time = time.time() - start_time
            memory_end = self.measure_memory()
            
            scalability_results[num_functions] = {
                "setup_time": setup_time,
                "inspection_time": inspection_time,
                "memory_usage": memory_end - memory_start,
                "functions_found": result.get("total_objectives", 0) + result.get("total_constraints", 0)
            }
            
            print(f"  Setup time: {setup_time*1000:.1f} ms")
            print(f"  Inspection time: {inspection_time*1000:.1f} ms")
            print(f"  Memory usage: {memory_end - memory_start:.1f} MB")
            print(f"  Functions found: {scalability_results[num_functions]['functions_found']}")
        
        self.benchmarks["scalability"] = scalability_results
        return scalability_results
    
    def benchmark_optimization_convergence(self):
        """Benchmark optimization convergence with new features."""
        print("\n" + "="*60)
        print("PERFORMANCE BENCHMARK: Optimization Convergence")
        print("="*60)
        
        # Clear all existing functions
        structures = ["PTV70", "PTV63", "PAROTID_LT", "PAROTID_RT", "SPINAL_CORD"]
        for struct in structures:
            try:
                self.engine.clear_all_objectives(struct)
            except:
                pass
        
        # Set up basic optimization problem
        self.engine.add_optimization_objective("PTV70", "square_deviation", 70.0, 1000.0, rationale="Convergence test")
        self.engine.add_optimization_objective("PTV63", "square_deviation", 63.0, 1000.0, rationale="Convergence test")
        self.engine.add_optimization_objective("PAROTID_LT", "max_dose", 25.0, 500.0, rationale="Convergence test")
        self.engine.add_optimization_objective("SPINAL_CORD", "max_dose", 45.0, 800.0, rationale="Convergence test")
        
        # Set optimizer for quick test
        self.engine.set_optimizer(optimizer_type="fmincon", max_iterations=10)
        
        # Run optimization and measure performance
        print("Running optimization (limited iterations for benchmark)...")
        start_time = time.time()
        memory_start = self.measure_memory()
        
        result = self.engine.optimize_fluence()
        
        optimization_time = time.time() - start_time
        memory_end = self.measure_memory()
        
        convergence_data = {
            "optimization_time": optimization_time,
            "memory_usage": memory_end - memory_start,
            "success": result.get("success", False),
            "optimization_analysis": result.get("optimization_analysis", {})
        }
        
        self.benchmarks["optimization_convergence"] = convergence_data
        
        print(f"Optimization time: {optimization_time:.2f} seconds")
        print(f"Memory usage during optimization: {memory_end - memory_start:.1f} MB")
        print(f"Optimization success: {result.get('success', False)}")
        
        if result.get("optimization_analysis"):
            analysis = result["optimization_analysis"]
            print(f"Final objective value: {analysis.get('final_objective', 'N/A')}")
            print(f"Convergence status: {analysis.get('convergence_status', 'N/A')}")
        
        return convergence_data
    
    def run_performance_benchmarks(self):
        """Run complete performance benchmark suite."""
        print("="*80)
        print("COMPREHENSIVE PERFORMANCE BENCHMARKS")
        print("Testing performance impact of new optimization features")
        print("="*80)
        
        start_time = time.time()
        self.baseline_memory = self.measure_memory()
        
        try:
            # Run all benchmarks
            self.benchmark_tool_execution()
            self.benchmark_scalability()
            self.benchmark_optimization_convergence()
            
            # Overall summary
            total_time = time.time() - start_time
            final_memory = self.measure_memory()
            
            print("\n" + "="*80)
            print("PERFORMANCE BENCHMARK SUMMARY")
            print("="*80)
            
            print(f"Total benchmark time: {total_time:.2f} seconds")
            print(f"Memory overhead: {final_memory - self.baseline_memory:.1f} MB")
            
            # Performance analysis
            self.analyze_performance()
            
            # Save results
            self.save_benchmark_results(total_time)
            
            return True
            
        except Exception as e:
            print(f"❌ Benchmark execution error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.cleanup()
    
    def analyze_performance(self):
        """Analyze performance results and provide recommendations."""
        print("\nPerformance Analysis:")
        
        # Tool timing analysis
        if "tool_timings" in self.benchmarks:
            timings = self.benchmarks["tool_timings"]
            slowest_tool = max(timings, key=timings.get)
            fastest_tool = min(timings, key=timings.get)
            
            print(f"  Fastest tool: {fastest_tool} ({timings[fastest_tool]*1000:.1f} ms)")
            print(f"  Slowest tool: {slowest_tool} ({timings[slowest_tool]*1000:.1f} ms)")
            
            # Check if comprehensive inspection is reasonable
            if timings.get("comprehensive_inspection", 0) > 1.0:
                print("  ⚠️ Comprehensive inspection is slow (>1s) - consider optimization")
            else:
                print("  ✅ Comprehensive inspection performance is good")
        
        # Scalability analysis
        if "scalability" in self.benchmarks:
            scalability = self.benchmarks["scalability"]
            
            # Check if performance degrades linearly
            times_20 = scalability.get(20, {}).get("inspection_time", 0)
            times_5 = scalability.get(5, {}).get("inspection_time", 0)
            
            if times_20 > 0 and times_5 > 0:
                scaling_factor = times_20 / times_5
                print(f"  Scalability factor (20 vs 5 functions): {scaling_factor:.1f}x")
                
                if scaling_factor > 8:  # Should be roughly 4x for linear scaling
                    print("  ⚠️ Performance degradation with many functions")
                else:
                    print("  ✅ Good scalability performance")
        
        # Optimization convergence analysis
        if "optimization_convergence" in self.benchmarks:
            convergence = self.benchmarks["optimization_convergence"]
            
            if convergence.get("optimization_time", 0) > 60:
                print("  ⚠️ Optimization is slow (>1 min) - check setup")
            else:
                print("  ✅ Optimization performance is reasonable")
    
    def save_benchmark_results(self, total_time: float):
        """Save benchmark results to file."""
        benchmark_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_execution_time": total_time,
            "baseline_memory": self.baseline_memory,
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
                "python_version": sys.version
            },
            "benchmarks": self.benchmarks
        }
        
        results_file = "test_logs/performance_benchmark_results.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(benchmark_data, f, indent=2)
        
        print(f"\n📁 Benchmark results saved to: {results_file}")
    
    def cleanup(self):
        """Clean up after benchmarking."""
        try:
            self.engine.stop_engine()
            print("\n🧹 Benchmark cleanup completed.")
        except:
            pass

def main():
    """Main execution."""
    benchmark = PerformanceBenchmark()
    
    try:
        success = benchmark.run_performance_benchmarks()
        return success
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during benchmarking: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

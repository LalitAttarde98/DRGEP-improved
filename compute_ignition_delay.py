import cantera as ct
import numpy as np
import matplotlib.pyplot as plt
import time

def calculate_ignition_delay(gas, temperature, pressure, fuel, oxidizer, equivalence_ratio):

    gas.TP = temperature, pressure
    gas.set_equivalence_ratio(phi=equivalence_ratio, fuel=fuel, oxidizer=oxidizer)

    reactor = ct.IdealGasReactor(gas)
    sim = ct.ReactorNet([reactor])
    sim.rtol = 1e-6
    sim.atol = 1e-12
    #sim.max_time_step = 1e-4 
    
    times = []
    temps = []
    max_simulation_time = 1.0
    timed_out = False
    timeout_sec = 600
    start_time = time.monotonic()
    
    try:
        while sim.time < max_simulation_time:
            sim.step()
            if time.monotonic() - start_time > timeout_sec:
                timed_out = True
                break
            times.append(sim.time)
            temps.append(reactor.T)
    except ct._utils.CanteraError as e:
        print(f"Integration failed: {e}")
        times = []
        temps = []

    if not times or (temps[-1] - temps[0]) < 400 or timed_out: 
        return None
    else:
        temps_arr = np.array(temps)
        times_arr = np.array(times)
        
        max_grad_index = np.argmax(np.gradient(temps_arr, times_arr))
        ignition_delay_sec = times_arr[max_grad_index] 
        
        return ignition_delay_sec

def main():
    mech1_path = 'docs/C3MechV4.0.1_44IA_C0-C3-C4_N_LT-HT_Cantera.yaml' 
    mech2_path = '/home/lattarde/workspace/lattarde/bevfusion/mmdet3d/ops/voxel/src/pyMARS/c4h10_multipath_158.yaml' 
    
    # Initial conditions
    pressure = 10.0 * ct.one_atm    
    equivalence_ratio = 1.0         
    fuel = 'C4H10'                  
    oxidizer = "O2:0.21,N2:0.79"    
    temperatures = np.linspace(600, 1600, 20) # Kelvin
    
    # ---------------------
    gas1 = ct.Solution(mech1_path)
    gas2 = ct.Solution(mech2_path)
    
    delays_mech1 = []
    delays_mech2 = []
    
    print(f"Calculating ignition delays for {fuel} / {oxidizer} mixture at {pressure/ct.one_atm:.1f} atm")
    print(f"{'Temperature (K)'} | {'Mech 1 Delay (ms)'} | {'Mech 2 Delay (ms)'}")
    print("-" * 65)

    for T in temperatures:
        delay1 = calculate_ignition_delay(gas1, T, pressure, fuel, oxidizer, equivalence_ratio)
        delay1_ms = delay1 * 1000.0 if delay1 is not None else None
        delays_mech1.append(delay1_ms)
        
        delay2 = calculate_ignition_delay(gas2, T, pressure, fuel, oxidizer, equivalence_ratio)
        delay2_ms = delay2 * 1000.0 if delay2 is not None else None
        delays_mech2.append(delay2_ms)
        
        d1_str = f"{delay1_ms:.4f}" if delay1_ms is not None else "Did not ignite"
        d2_str = f"{delay2_ms:.4f}" if delay2_ms is not None else "Did not ignite"
        print(f"{T:<20.2f} | {d1_str:<20} | {d2_str:<20}")

    valid_indices = [i for i in range(len(temperatures)) if delays_mech1[i] is not None and delays_mech2[i] is not None]
    
    if not valid_indices:
        print("No successful ignitions recorded. Check mechanism, thermodynamics, or increase max_simulation_time.")
        return

    temp_valid = temperatures[valid_indices]
    delays_mech1_valid = np.array(delays_mech1)[valid_indices]
    delays_mech2_valid = np.array(delays_mech2)[valid_indices]

    inverse_T = 1000.0 / temp_valid

    plt.figure(figsize=(8, 6))
    
    plt.semilogy(inverse_T, delays_mech1_valid, 'o-', linewidth=2, label=f'Detailed Mechanism {(gas1.n_species)}')
    plt.semilogy(inverse_T, delays_mech2_valid, 's--', linewidth=2, label=f'Reduced Mechanism {(gas2.n_species)}')
    
    plt.xlabel('1000 / T (1/K)', fontsize=12)
    plt.ylabel('Ignition Delay (ms)', fontsize=12)
    plt.title(f'Ignition Delay Comparison\n(P = {pressure/ct.one_atm:.1f} atm, $\phi$ = {equivalence_ratio}, {fuel} in Air)', fontsize=14)
    
    plt.legend(fontsize=12)
    plt.grid(True, which="both", ls="--", alpha=0.7)
    plt.tight_layout()
    
    plt.savefig('ignition_delay_comparison.png', dpi=300)
    plt.show()

if __name__ == '__main__':
    main()
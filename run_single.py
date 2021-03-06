from data_interface import query_ways_postgis_db
from data_interface import query_nodes_postgis_db

from data_wrangling import get_accepted_highways
from data_wrangling import create_node_dict
from data_wrangling import create_highway_dict
from data_wrangling import get_required_nodes
from data_wrangling import find_intersections
from data_wrangling import create_state_space_representations
from data_wrangling import remove_unconnected_states

from simulation import simulate_route
from simulation import simulate_observations

from hmm import transition_probabilties_by_weighting_route_length
from hmm import viterbi
from hmm import backward_recursions
from hmm import forward_recursions

from hmm_extensions import emission_probabilities

from visualization import plot_results

from tools import state_sequence_to_node_sequence
from tools import get_accuracy_of_estimate
from tools import generate_base_locations

from naive_estimation import spatially_closest_states

import random
import numpy as np

import sys

np.random.seed(3265)
random.seed(3265)

password = sys.argv[1]

print("Fetching and processing data..")

bbox = [10.3914799928,63.4271680224,10.4036679506,63.4323125008]
ways = query_ways_postgis_db(bbox, password)

accepted_highways = get_accepted_highways(ways)

required_nodes = get_required_nodes(accepted_highways)

highway_dict = create_highway_dict(accepted_highways)

nodes = query_nodes_postgis_db(required_nodes, password)

node_dict = create_node_dict(nodes)

untrimmed_state_space = create_state_space_representations(accepted_highways, node_dict)
state_space = remove_unconnected_states(untrimmed_state_space)

print("Size of state space: {}".format(len(state_space)))

intersections = find_intersections(highway_dict, node_dict)

starting_highway = random.choice(list(highway_dict.keys()))
starting_node = random.choice(highway_dict[starting_highway]['data']['nd'])

speed_limit = 8
polling_frequency = 1/15
gps_variance = 5
measurement_variance = 1
transition_decay = 1/500
maximum_route_length = speed_limit/polling_frequency*2
no_of_bases = 50
base_max_range = 50
route_length = 200

print("Simulating route..")

base_locations = generate_base_locations(bbox, no_of_bases)

simulated_route = simulate_route(highway_dict, starting_node, starting_highway, intersections, route_length)
gps_measurements, signal_measurements, measurement_states = simulate_observations(simulated_route, node_dict, gps_variance, polling_frequency,\
 [speed_limit]*len(simulated_route), base_locations, np.array([base_max_range]*no_of_bases), state_space)


print("Calculating transition probabilities..")
tp = transition_probabilties_by_weighting_route_length(state_space, transition_decay, maximum_route_length)

print("Calculating emission probabilities..")
ep = emission_probabilities(gps_measurements, measurement_variance, signal_measurements, base_locations, np.array([500]*no_of_bases), state_space)

N = len(state_space)

print("Running Viterbi..")
estimated_states = viterbi(tp, ep, np.array([1/N]*N))


naive_estimate = spatially_closest_states(gps_measurements, state_space)

print("Accuracy with naive method: {}".format(np.mean(measurement_states == naive_estimate)))
print("Accuracy with hidden markov model: {}".format(np.mean(estimated_states == measurement_states)))
from DYSOLUTION import Dynamic_solution
from instance import generate_instance


dataset = [[25, 25, 2, 20],
           [25, 5, 5, 20],
           [25, 25, 5, 20],
           [25, 25, 10, 20]]

time_limit = 300

for i in dataset:
    new = generate_instance(n_orders=i[0], n_racks=i[1], capacity=i[2], n_items=i[3])
    solver = Dynamic_solution(instance=new, time_limit=time_limit)
    solver.run_DP()
    solver.save_sample_matric("dataset")

from bw_info import BwInfo
import json


class BwInfoSSYNC(BwInfo):
    
    def parse_osinfo(self, osinfo):
        data = json.loads(osinfo)
        for node in data:
            self.count[node] = data[node]
    
    def _write_experimental_results(self, aggregated_results):
        if len(self.last_bw_info) == self.bw_info_to_average:
            averaged_aggregated_results = dict()
            for tmp_result in self.last_bw_info:
                for node in tmp_result:
                    if node not in averaged_aggregated_results:
                        averaged_aggregated_results[node] = {}
                    for source in tmp_result[node]:
                        if source not in averaged_aggregated_results[node]:
                            averaged_aggregated_results[node][source] = {}
                        for device in tmp_result[node][source]:
                            if device not in averaged_aggregated_results[node][source]:
                                averaged_aggregated_results[node][source][device] = 0.0
                            averaged_aggregated_results[node][source][device] += tmp_result[node][source][device]
                
            print
            total_sum = 0
            
            for node in averaged_aggregated_results:
                for source in averaged_aggregated_results[node]:
                    for device in averaged_aggregated_results[node][source]:
                        value = averaged_aggregated_results[node][source][device]/self.bw_info_to_average
                        print "FROM " + source.split(':')[1] + " TO " + node.split(':')[0] + " ON " + device + " -> " + \
                              str("{:,}".format(int(value)) + " bytes")
                        total_sum += int(value)

            #self.output.write(str(int(total_sum))+"\n")
            #self.output.flush()

            self.last_bw_info = list()
              
        # Aggregate results for further averages
        self.last_bw_info.append(aggregated_results)

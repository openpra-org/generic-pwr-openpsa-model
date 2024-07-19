import os
from opsa_mef import ModelData, FaultTreeOpenPSA, EventTree
import xml.etree.ElementTree as ET
import json
import copy


class JSONtoXMLConverter:
    def __init__(self, parsed_json_object):
        self.parsed_json_object = parsed_json_object

    def convert_to_xml(self):
        initiating_event = self._convert_initiatingevent_to_xml()
        event_trees = self._convert_sequencelist_to_eventteee
        fault_trees = self._convert_faulttreelist_to_faulttree()
        model_data = self._convert_eventlist_to_modeldata()

        # Convert each FaultTree object to XML
        xml_event_trees = event_trees.to_xml()
        xml_fault_trees = [ft.to_xml() for ft in fault_trees]
        xml_model_data = model_data.to_xml()

        # Create a root XML element to hold both fault trees and model data
        root_element = ET.Element('')

        root_element.append(initiating_event)
        # Append XML representation of event trees to the root element
        root_element.append(xml_event_trees)

        # Append XML representation of fault trees to the root element
        for xml_fault_tree in xml_fault_trees:
            root_element.append(xml_fault_tree)

        # Append XML representation of model data to the root element
        root_element.append(xml_model_data)

        return root_element

    def _convert_initiatingevent_to_xml(self):
        event_tree_name = self.parsed_json_object.saphiresolveinput.get('header', {}).eventtree.name
        initiating_event_id = "INIT"+str(self.parsed_json_object.saphiresolveinput.get('header', {}).eventtree.initevent)

        initiating_event_element = ET.Element('define-initiating-event',
                                               {'name': initiating_event_id, 'event-tree': event_tree_name})

        return initiating_event_element
    def _convert_eventlist_to_modeldata(self):
        model_data = ModelData()

        # Accessing eventlist attribute directly from parsed JSON object
        eventlist = self.parsed_json_object.saphiresolveinput.get('eventlist', [])

        for event in eventlist:
                if event.corrgate == "0":
                    name = "BE"+ event.id
                    label = event.name
                    value = event.value

                    if label in ["<TRUE>", "<FALSE>", "<PASS>"]:
                        continue

                    # Check if the value is "0.00000E+00"
                    if value == "0.00000E+00":
                        float_value = value
                    else:
                        # Format other float values using scientific notation with six digits of precision
                        float_value = "{:.6E}".format(float(value))

                    model_data.add_basic_event(name, label=label, float_value=float_value)

        return model_data

    def _convert_faulttreelist_to_faulttree(self):
        faulttreelist = self.parsed_json_object.saphiresolveinput.get("faulttreelist", [])
        combined_fault_trees = []

        for ft_data in faulttreelist:
            ftheader = ft_data.ftheader  # Accessing attributes directly
            name = "FT"+str(ftheader.get("ftid"))  # Accessing name attribute of ftheader
            ft = FaultTreeOpenPSA(name)

            gatelist = ft_data.gatelist
            if gatelist is not None:  # Check if gatelist is not None
                first_gate = True  # Flag to check if the gate is the first one
                for gate_data in gatelist:
                    if first_gate:
                        gate_id = "TOP"
                        first_gate = False  # Set flag to False after processing the first gate
                    else:
                        gate_id = "G" + str(gate_data.gateid)
                    gate_type = gate_data.gatetype
                    gate_inputs = gate_data.gateinput
                    event_inputs = gate_data.eventinput
                    complement_event_inputs = gate_data.compeventinput

                    if gate_type in ["or", "and"]:
                        ft.add_gate(gate_id, gate_type)
                    elif "/" in gate_type:  # Custom gate type like "2/3"
                        min_required = gate_type.split("/")[0]
                        ft.add_gate(gate_id, min_required)  # Use min_required as gate_type
                    if gate_inputs is not None:
                        # Check if gate_inputs is an integer (indicating it's empty)
                        if isinstance(gate_inputs, int):
                            gate_inputs = []
                        else:
                            # Convert gate_inputs to a list if it's not already one
                            if not isinstance(gate_inputs, list):
                                gate_inputs = [gate_inputs]
                        # Iterate through gate_inputs and add each input individually
                        for input_name in gate_inputs:
                            if input_name is not None:
                                input_name = "G"+ str(input_name)
                                ft.add_gate_input(gate_id, input_name)
                    if event_inputs is not None:
                        # Check if gate_inputs is an integer (indicating it's empty)
                        if isinstance(event_inputs, int):
                            event_inputs = []  # Convert it to an empty list
                        else:
                            # Convert gate_inputs to a list if it's not already one
                            if not isinstance(event_inputs, list):
                                event_inputs = [event_inputs]
                        # Iterate through event_inputs and add each input individually
                        for input_name in event_inputs:
                            if input_name is not None:
                                input_name = "BE"+ str(input_name)
                                ft.add_basic_event(gate_id, input_name)

                    if complement_event_inputs is not None:
                        # Check if gate_inputs is an integer (indicating it's empty)
                        if isinstance(complement_event_inputs, int):
                            complement_event_inputs = []
                        else:
                            # Convert gate_inputs to a list if it's not already one
                            if not isinstance(complement_event_inputs, list):
                                complement_event_inputs = [complement_event_inputs]
                        # Iterate through complement_event_inputs and add each input individually
                        for input_name in complement_event_inputs:
                            if input_name is not None:
                                input_name = "BE"+ str(input_name)
                                ft.add_comp_event(gate_id, input_name)

            combined_fault_trees.append(ft)

        return combined_fault_trees

    @property
    def _convert_sequencelist_to_eventteee(self):
        # Accessing sysgatelist attribute directly from parsed JSON object
        sysgatelist = self.parsed_json_object.saphiresolveinput.get('sysgatelist', [])
        # Accessing sequencelist attribute directly from parsed JSON object
        sequencelist = self.parsed_json_object.saphiresolveinput.get('sequencelist', [])

        event_tree_name = self.parsed_json_object.saphiresolveinput.get('header', {}).eventtree.name
        event_tree = EventTree(event_tree_name)

        # Iterate over both lists simultaneously
        functional_event_list = []
        for functional_event in sysgatelist:
            functional_event_name = "FE"+str(functional_event.id)
            event_tree.functional_events.append(functional_event_name)
            functional_event_list.append(functional_event_name)

        faulttreelist = self.parsed_json_object.saphiresolveinput.get("faulttreelist", [])
        top_gate_list = []
        ft_id_list = []
        for ft_data in faulttreelist:
            if ft_data.gatelist is not None:  # Check if gatelist is not None
                top_gate_id = "G" + str(ft_data.gatelist[0].gateid)
                ft_id = "FT" + str(ft_data.ftheader.get("ftid"))
                top_gate_list.append(top_gate_id)
                ft_id_list.append(ft_id)


        logiclist =[]
        seq_id_list = []
        for sequence in sequencelist:
            seqid = "S"+str(sequence.seqid)
            seq_id_list.append(seqid)
            event_tree.sequences.append(seqid)

            logic_list = sequence.logiclist
            logiclist.append(logic_list)

        logiclist = self.convert_logiclist_to_binary(logiclist)

        sq_count = self.parsed_json_object.saphiresolveinput.get('header', {}).sqcount
        # Get the current directory of the Python script
        current_directory = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_directory, 'sequence_data.json')
        # Load existing data from the JSON file (if any)
        # Load existing data from the JSON file (if any)
        existing_data = {}
        try:
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}

        # Update the existing data with the new data
        existing_data[event_tree_name+"-"+str (sq_count)] = logiclist

        # Save the updated dictionary to a JSON file
        with open(file_path, 'w') as f:
            json.dump(existing_data, f)

        return event_tree

    def decimal_to_binary(self, dec):
        """Convert decimal to binary"""
        binary = bin(dec)[2:]  # Convert decimal to binary, excluding the '0b' prefix
        return binary

    def decimal_to_binary_id(self, dec):
        """Convert decimal to binary, extract the last 17 digits, and return their decimal representation."""
        binary = bin(dec)[2:]  # Convert decimal to binary, excluding the '0b' prefix
        last_17_binary = binary[-17:]  # Extract the last 17 digits

        # Convert the last 17 binary digits back to a decimal number
        decimal_representation = int(last_17_binary, 2) if len(last_17_binary) > 0 else 0
        return decimal_representation

    def deep_copy_dict(self, dictionary):
        """
        Deep copy a dictionary and all nested dictionaries.
        """
        return {key: (self.deep_copy_dict(value) if isinstance(value, dict) else copy.deepcopy(value)) for key, value in
                dictionary.items()}

    def convert_logiclist_to_binary(self, logiclist):
        binary_logiclist = []

        for sublist in logiclist:
            binary_sublist = []
            for decimal_number in sublist:
                # Check the length of the decimal number before conversion
                suffix = 'f' if len(str(decimal_number)) == 6 else 's'
                binary_number = self.decimal_to_binary_id(decimal_number)
                binary_sublist.append(suffix + str(binary_number))
            binary_logiclist.append(binary_sublist)

        return binary_logiclist















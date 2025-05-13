SELECT

 o.Operation_Code
,o.Operation_Type
,o.Inventory_Type
,o.Defect_Log
,o.Material
,o.Rework
,o.Ship 'Allow Ship'
,o.Default_Operation 'Default'
,o.Shipping_Operation
,o.Uses_Tools
,o.Variable_BOM_Qty 'Variable BOM'
,o.Job_Quantity_Defective_Increase
,o.Final_Operation
,o.unit 'Inventory Unit'
,o.Denominator_Unit
,o.Fixed_Run_Time
,o.Delay_Before
,o.Delay_After
,o.Note

FROM part_v_operation o
ORDER BY o.operation_code

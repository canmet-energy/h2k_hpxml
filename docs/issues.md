### Issues:

#### Attached Surfaces
If you tell HPXML that the house is attached (i.e. row house end), but do not specify any attached surfaces then the calculation will break. This is a problem because attached surfaces are not modeled in HOT2000. The following workaround is proposed.

1. Check the ratio of exposed foundation perimeter to foundation perimeter. The non-exposed fraction will represent the amount of attached wall perimeter we need to add.
2. Filter all non buffered HOT2000 walls and calculate their total area, average wall height, and most common R-value.
3. Multiply the total non-buffered wall area from (2.) by the non-exposed fraction from (1.) to determine the area of the attached wall.
4. Create a new wall component with the attached wall area, average wall height, and most common R-value. 

All added walls from this method will have their ExteriorAdjacentTo field set to "other housing unit", meaning they should be adiabatic surfaces since the exterior temperature will be the same as the interior temperature for this location type.

This method requires testing with houses having:
- Complex multi-component foundations
- Only exposed floors as foundations (will need to use a common ratio)

#### ConditionedFloorArea restrictions
Error message: "Error: Expected ConditionedFloorArea to be greater than or equal to the sum of conditioned slab/floor areas."
This error message means that we cannot include floors above a basement in the model. 
However, the workflow does require a floor above a crawlspace.
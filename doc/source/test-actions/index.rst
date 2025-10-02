Test Actions
============

Execute Scade One model test actions.

Test execution
--------------

.. jinja:: tests-exec

    {{ description }}

    {{ inputs_table }}

    {{ outputs_table }}

    Example
    +++++++

    {% for filename, title in examples %}
    .. dropdown:: {{ title }}
       :animate: fade-in

       .. literalinclude:: examples/{{ filename }}
          :language: yaml

    {% endfor %}

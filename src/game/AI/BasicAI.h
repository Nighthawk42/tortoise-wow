/*
 * Compatibility base used by Eluna's VMangos adapter.
 *
 * This core exposes the same callback surface on CreatureAI but does not use
 * VMangos' BasicAI class name. Keeping the small bridge in the host avoids
 * carrying local modifications inside the pinned Eluna submodule.
 */

#ifndef MANGOS_BASICAI_H
#define MANGOS_BASICAI_H

#include "CreatureAI.h"

class BasicAI : public CreatureAI
{
    public:
        explicit BasicAI(Creature* creature) : CreatureAI(creature) {}
};

#endif

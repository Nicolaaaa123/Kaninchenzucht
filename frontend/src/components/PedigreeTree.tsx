import { Link } from "react-router-dom";
import type { PedigreeNode } from "../api/types";
import { coiLabel, coiRiskClass } from "../utils/inbreeding";

function AncestorNode({ node }: { node: PedigreeNode | null }) {
  if (!node) {
    return (
      <div className="pedigree-branch">
        <div className="pedigree-node empty">
          <div className="pedigree-name">unbekannt</div>
        </div>
      </div>
    );
  }

  const hasParents = !!(node.mother || node.father);

  return (
    <div className="pedigree-branch">
      <Link to={`/tiere/${node.id}`} className="pedigree-node">
        <div className="pedigree-chip">{node.chip_number}</div>
        {node.name && <div className="pedigree-name">{node.name}</div>}
        {node.breed_name && <div className="pedigree-breed">{node.breed_name}</div>}
        {node.inbreeding_coefficient > 0 && (
          <div className={`badge ${coiRiskClass(node.inbreeding_coefficient)}`} style={{ marginTop: 4 }}>
            COI {coiLabel(node.inbreeding_coefficient)}
          </div>
        )}
      </Link>
      {hasParents && (
        <div className="pedigree-parents">
          <AncestorNode node={node.mother} />
          <AncestorNode node={node.father} />
        </div>
      )}
    </div>
  );
}

export function PedigreeTree({ root }: { root: PedigreeNode }) {
  return (
    <div className="pedigree-tree">
      <div className="pedigree-branch">
        <div className="pedigree-node self">
          <div className="pedigree-chip">{root.chip_number}</div>
          {root.name && <div className="pedigree-name">{root.name}</div>}
        </div>
        <div className="pedigree-parents">
          <AncestorNode node={root.mother} />
          <AncestorNode node={root.father} />
        </div>
      </div>
    </div>
  );
}
